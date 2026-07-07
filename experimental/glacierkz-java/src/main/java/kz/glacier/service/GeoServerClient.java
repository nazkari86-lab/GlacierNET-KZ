package kz.glacier.service;

import kz.glacier.config.GeoServerConfig;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.Base64;
import java.util.Map;

@Service
@Slf4j
public class GeoServerClient {

    private final GeoServerConfig geoServerConfig;
    private final RestTemplate restTemplate;

    public GeoServerClient(GeoServerConfig geoServerConfig) {
        this.geoServerConfig = geoServerConfig;
        this.restTemplate = geoServerConfig.restTemplate();
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public boolean publishLayer(String layerName, String workspace, String storeName, String nativeName) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}/datastores/{store}/featuretypes")
                .buildAndExpand(workspace, storeName)
                .toUriString();

        String xml = """
                <featureType>
                    <name>%s</name>
                    <nativeName>%s</nativeName>
                    <title>%s</title>
                    <srs>EPSG:4326</srs>
                    <enabled>true</enabled>
                </featureType>
                """.formatted(layerName, nativeName, layerName);

        HttpHeaders headers = createAuthHeaders();
        headers.setContentType(MediaType.APPLICATION_XML);

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST,
                    new HttpEntity<>(xml, headers), String.class);
            log.info("Published layer: {} status={}", layerName, response.getStatusCode());
            return response.getStatusCode().is2xxSuccessful();
        } catch (ResourceAccessException e) {
            log.error("GeoServer connection error publishing layer {}: {}", layerName, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Failed to publish layer {}: {}", layerName, e.getMessage());
            return false;
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public boolean publishCoverage(String coverageName, String workspace, String storeName) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}/coveragestores/{store}/coverages")
                .buildAndExpand(workspace, storeName)
                .toUriString();

        String xml = """
                <coverage>
                    <name>%s</name>
                    <nativeName>%s</nativeName>
                    <title>%s</title>
                    <srs>EPSG:4326</srs>
                    <enabled>true</enabled>
                    <nativeCoverageName>%s</nativeCoverageName>
                </coverage>
                """.formatted(coverageName, coverageName, coverageName, coverageName);

        HttpHeaders headers = createAuthHeaders();
        headers.setContentType(MediaType.APPLICATION_XML);

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST,
                    new HttpEntity<>(xml, headers), String.class);
            log.info("Published coverage: {} status={}", coverageName, response.getStatusCode());
            return response.getStatusCode().is2xxSuccessful();
        } catch (ResourceAccessException e) {
            log.error("GeoServer connection error publishing coverage {}: {}", coverageName, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Failed to publish coverage {}: {}", coverageName, e.getMessage());
            return false;
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public boolean deleteLayer(String layerName, String workspace) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}/layers/{layer}")
                .buildAndExpand(workspace, layerName)
                .toUriString();

        HttpHeaders headers = createAuthHeaders();

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.DELETE,
                    new HttpEntity<>(headers), String.class);
            log.info("Deleted layer: {} status={}", layerName, response.getStatusCode());
            return response.getStatusCode().is2xxSuccessful();
        } catch (ResourceAccessException e) {
            log.error("GeoServer connection error deleting layer {}: {}", layerName, e.getMessage());
            throw e;
        } catch (Exception e) {
            log.error("Failed to delete layer {}: {}", layerName, e.getMessage());
            return false;
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public Map<String, Object> getLayerInfo(String layerName, String workspace) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}/layers/{layer}.json")
                .buildAndExpand(workspace, layerName)
                .toUriString();

        HttpHeaders headers = createAuthHeaders();

        try {
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.GET,
                    new HttpEntity<>(headers), Map.class);
            return response.getBody();
        } catch (Exception e) {
            log.error("Failed to get layer info for {}: {}", layerName, e.getMessage());
            return Map.of("error", e.getMessage());
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public boolean createWorkspace(String workspaceName) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces")
                .toUriString();

        String xml = """
                <workspace>
                    <name>%s</name>
                </workspace>
                """.formatted(workspaceName);

        HttpHeaders headers = createAuthHeaders();
        headers.setContentType(MediaType.APPLICATION_XML);

        try {
            ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST,
                    new HttpEntity<>(xml, headers), String.class);
            log.info("Created workspace: {} status={}", workspaceName, response.getStatusCode());
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.error("Failed to create workspace {}: {}", workspaceName, e.getMessage());
            return false;
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public Map<String, Object> getWorkspaceInfo(String workspaceName) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}.json")
                .buildAndExpand(workspaceName)
                .toUriString();

        HttpHeaders headers = createAuthHeaders();

        try {
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.GET,
                    new HttpEntity<>(headers), Map.class);
            return response.getBody();
        } catch (Exception e) {
            log.error("Failed to get workspace info for {}: {}", workspaceName, e.getMessage());
            return Map.of("error", e.getMessage());
        }
    }

    @Retryable(value = ResourceAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 1000))
    public Map<String, Object> getCoverageStoreInfo(String storeName, String workspace) {
        String url = UriComponentsBuilder.fromHttpUrl(geoServerConfig.restUrl())
                .path("/workspaces/{workspace}/coveragestores/{store}.json")
                .buildAndExpand(workspace, storeName)
                .toUriString();

        HttpHeaders headers = createAuthHeaders();

        try {
            ResponseEntity<Map> response = restTemplate.exchange(url, HttpMethod.GET,
                    new HttpEntity<>(headers), Map.class);
            return response.getBody();
        } catch (Exception e) {
            log.error("Failed to get coverage store info for {}/{}: {}", workspace, storeName, e.getMessage());
            return Map.of("error", e.getMessage());
        }
    }

    private HttpHeaders createAuthHeaders() {
        HttpHeaders headers = new HttpHeaders();
        String credentials = geoServerConfig.username() + ":" + geoServerConfig.password();
        String encoded = Base64.getEncoder().encodeToString(credentials.getBytes());
        headers.set("Authorization", "Basic " + encoded);
        return headers;
    }
}
