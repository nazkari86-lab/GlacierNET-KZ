package kz.glacier.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.DefaultUriBuilderFactory;

import java.time.Duration;

@Configuration
public class GeoServerConfig {

    @Value("${geoserver.url}")
    private String geoserverUrl;

    @Value("${geoserver.username}")
    private String username;

    @Value("${geoserver.password}")
    private String password;

    @Value("${geoserver.workspace}")
    private String workspace;

    @Value("${geoserver.timeout:30000}")
    private int timeout;

    @Bean(name = "geoServerRestTemplate")
    public RestTemplate geoServerRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(timeout));
        factory.setReadTimeout(Duration.ofMillis(timeout));

        RestTemplate restTemplate = new RestTemplateBuilder()
                .rootUri(geoserverUrl)
                .basicAuthentication(username, password)
                .setConnectTimeout(Duration.ofMillis(timeout))
                .setReadTimeout(Duration.ofMillis(timeout))
                .defaultUriVariables(java.util.Map.of(
                        "workspace", workspace
                ))
                .build();

        return restTemplate;
    }

    @Bean
    public GeoServerProperties geoServerProperties() {
        return new GeoServerProperties(geoserverUrl, username, password, workspace, timeout);
    }

    public record GeoServerProperties(
            String url,
            String username,
            String password,
            String workspace,
            int timeout
    ) {
        public String layersUrl() {
            return url + "/rest/workspaces/" + workspace + "/layers";
        }

        public String coveragesUrl() {
            return url + "/rest/workspaces/" + workspace + "/coveragestores";
        }

        public String wmsUrl() {
            return url + "/" + workspace + "/wms";
        }

        public String wfsUrl() {
            return url + "/" + workspace + "/wfs";
        }
    }
}
