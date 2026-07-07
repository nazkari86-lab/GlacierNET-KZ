package api

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/glacierkz/glacierkz-go/pkg/models"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
	maxRetries int
	retryDelay time.Duration
	apiKeys    []string
}

type ClientOption func(*Client)

func WithTimeout(timeout time.Duration) ClientOption {
	return func(c *Client) {
		c.httpClient.Timeout = timeout
	}
}

func WithRetries(max int, delay time.Duration) ClientOption {
	return func(c *Client) {
		c.maxRetries = max
		c.retryDelay = delay
	}
}

func WithAPIKeys(keys []string) ClientOption {
	return func(c *Client) {
		c.apiKeys = keys
	}
}

func WithMaxConns(max int) ClientOption {
	return func(c *Client) {
		transport := c.httpClient.Transport.(*http.Transport)
		transport.MaxIdleConns = max
		transport.MaxIdleConnsPerHost = max / 2
	}
}

func NewClient(baseURL string, opts ...ClientOption) *Client {
	c := &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
			Transport: &http.Transport{
				MaxIdleConns:        100,
				MaxIdleConnsPerHost: 20,
				IdleConnTimeout:     90 * time.Second,
			},
		},
		maxRetries: 3,
		retryDelay: 1 * time.Second,
	}
	for _, opt := range opts {
		opt(c)
	}
	return c
}

func (c *Client) Get(ctx context.Context, path string, result any) error {
	return c.do(ctx, http.MethodGet, path, nil, result)
}

func (c *Client) Post(ctx context.Context, path string, body any, result any) error {
	return c.do(ctx, http.MethodPost, path, body, result)
}

func (c *Client) Put(ctx context.Context, path string, body any, result any) error {
	return c.do(ctx, http.MethodPut, path, body, result)
}

func (c *Client) Delete(ctx context.Context, path string) error {
	return c.do(ctx, http.MethodDelete, path, nil, nil)
}

func (c *Client) do(ctx context.Context, method, path string, body any, result any) error {
	var lastErr error
	for attempt := 0; attempt <= c.maxRetries; attempt++ {
		if attempt > 0 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(c.retryDelay * time.Duration(attempt)):
			}
		}

		err := c.doOnce(ctx, method, path, body, result)
		if err == nil {
			return nil
		}

		lastErr = err
		if !isRetryable(err) {
			return err
		}
	}
	return fmt.Errorf("max retries exceeded: %w", lastErr)
}

func (c *Client) doOnce(ctx context.Context, method, path string, body any, result any) error {
	fullURL := c.baseURL + "/" + strings.TrimLeft(path, "/")

	var bodyReader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("marshaling request body: %w", err)
		}
		bodyReader = bytes.NewReader(data)
	}

	req, err := http.NewRequestWithContext(ctx, method, fullURL, bodyReader)
	if err != nil {
		return fmt.Errorf("creating request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "application/json")
	req.Header.Set("User-Agent", "glacierkz-go/1.0")

	if len(c.apiKeys) > 0 {
		req.Header.Set("X-API-Key", c.apiKeys[0])
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return &RequestError{Err: err, Retryable: true}
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return &RequestError{Err: fmt.Errorf("reading response: %w", err), Retryable: true}
	}

	if resp.StatusCode >= 500 {
		return &RequestError{
			Err:       fmt.Errorf("server error %d: %s", resp.StatusCode, string(respBody)),
			StatusCode: resp.StatusCode,
			Retryable: true,
		}
	}

	if resp.StatusCode == http.StatusNotFound {
		return &RequestError{
			Err:        fmt.Errorf("resource not found"),
			StatusCode: resp.StatusCode,
			Retryable:  false,
		}
	}

	if resp.StatusCode >= 400 {
		var errResp models.ErrorResponse
		if json.Unmarshal(respBody, &errResp) == nil {
			return &RequestError{
				Err:        fmt.Errorf("API error: %s", errResp.Message),
				StatusCode: resp.StatusCode,
				Retryable:  false,
			}
		}
		return &RequestError{
			Err:        fmt.Errorf("client error %d: %s", resp.StatusCode, string(respBody)),
			StatusCode: resp.StatusCode,
			Retryable:  false,
		}
	}

	if result != nil && len(respBody) > 0 {
		if err := json.Unmarshal(respBody, result); err != nil {
			return fmt.Errorf("decoding response: %w", err)
		}
	}

	return nil
}

func isRetryable(err error) bool {
	if reqErr, ok := err.(*RequestError); ok {
		return reqErr.Retryable
	}
	return true
}

type RequestError struct {
	Err        error
	StatusCode int
	Retryable  bool
}

func (e *RequestError) Error() string {
	return e.Err.Error()
}

func (e *RequestError) Unwrap() error {
	return e.Err
}

func buildQueryString(params map[string]string) string {
	if len(params) == 0 {
		return ""
	}
	values := url.Values{}
	for k, v := range params {
		if v != "" {
			values.Set(k, v)
		}
	}
	if encoded := values.Encode(); encoded != "" {
		return "?" + encoded
	}
	return ""
}
