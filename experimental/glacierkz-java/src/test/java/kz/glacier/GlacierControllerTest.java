package kz.glacier;

import kz.glacier.controller.GlacierController;
import kz.glacier.dto.GlacierDto;
import kz.glacier.dto.PageResponse;
import kz.glacier.model.Glacier;
import kz.glacier.service.GlacierService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class GlacierControllerTest {
    
    @Mock
    private GlacierService glacierService;
    
    @InjectMocks
    private GlacierController glacierController;
    
    private Glacier testGlacier;
    private GlacierDto testGlacierDto;
    
    @BeforeEach
    void setUp() {
        testGlacier = new Glacier();
        testGlacier.setId(UUID.randomUUID());
        testGlacier.setName("Test Glacier");
        testGlacier.setCode("TG001");
        testGlacier.setRegion("Central Asia");
        testGlacier.setMountainRange("Tien Shan");
        testGlacier.setCountry("Kazakhstan");
        testGlacier.setAreaKm2(5.5);
        testGlacier.setLengthKm(3.2);
        testGlacier.setElevationMin(3200.0);
        testGlacier.setElevationMax(4100.0);
        testGlacier.setStatus("ACTIVE");
        testGlacier.setCreatedAt(LocalDateTime.now());
        testGlacier.setUpdatedAt(LocalDateTime.now());
        
        testGlacierDto = GlacierDto.of(testGlacier);
    }
    
    @Test
    void testGetAllGlaciers() {
        // Given
        Pageable pageable = PageRequest.of(0, 10);
        Page<Glacier> glacierPage = new PageImpl<>(Arrays.asList(testGlacier), pageable, 1);
        
        when(glacierService.findAll(any(Pageable.class))).thenReturn(glacierPage);
        
        // When
        ResponseEntity<PageResponse<GlacierDto>> response = 
            glacierController.getAllGlaciers(pageable);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(1, response.getBody().getContent().size());
        assertEquals("Test Glacier", response.getBody().getContent().get(0).getName());
        
        verify(glacierService).findAll(pageable);
    }
    
    @Test
    void testGetGlacierById() {
        // Given
        when(glacierService.findById(testGlacier.getId()))
            .thenReturn(Optional.of(testGlacier));
        
        // When
        ResponseEntity<GlacierDto> response = 
            glacierController.getGlacierById(testGlacier.getId());
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Test Glacier", response.getBody().getName());
        
        verify(glacierService).findById(testGlacier.getId());
    }
    
    @Test
    void testGetGlacierById_NotFound() {
        // Given
        UUID nonExistentId = UUID.randomUUID();
        when(glacierService.findById(nonExistentId))
            .thenReturn(Optional.empty());
        
        // When
        ResponseEntity<GlacierDto> response = 
            glacierController.getGlacierById(nonExistentId);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertNull(response.getBody());
        
        verify(glacierService).findById(nonExistentId);
    }
    
    @Test
    void testCreateGlacier() {
        // Given
        when(glacierService.save(any(Glacier.class)))
            .thenReturn(testGlacier);
        
        // When
        ResponseEntity<GlacierDto> response = 
            glacierController.createGlacier(testGlacierDto);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Test Glacier", response.getBody().getName());
        
        verify(glacierService).save(any(Glacier.class));
    }
    
    @Test
    void testUpdateGlacier() {
        // Given
        when(glacierService.findById(testGlacier.getId()))
            .thenReturn(Optional.of(testGlacier));
        when(glacierService.save(any(Glacier.class)))
            .thenReturn(testGlacier);
        
        // When
        ResponseEntity<GlacierDto> response = 
            glacierController.updateGlacier(testGlacier.getId(), testGlacierDto);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals("Test Glacier", response.getBody().getName());
        
        verify(glacierService).findById(testGlacier.getId());
        verify(glacierService).save(any(Glacier.class));
    }
    
    @Test
    void testUpdateGlacier_NotFound() {
        // Given
        UUID nonExistentId = UUID.randomUUID();
        when(glacierService.findById(nonExistentId))
            .thenReturn(Optional.empty());
        
        // When
        ResponseEntity<GlacierDto> response = 
            glacierController.updateGlacier(nonExistentId, testGlacierDto);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        assertNull(response.getBody());
        
        verify(glacierService).findById(nonExistentId);
        verify(glacierService, never()).save(any(Glacier.class));
    }
    
    @Test
    void testDeleteGlacier() {
        // Given
        when(glacierService.findById(testGlacier.getId()))
            .thenReturn(Optional.of(testGlacier));
        doNothing().when(glacierService).deleteById(testGlacier.getId());
        
        // When
        ResponseEntity<Void> response = 
            glacierController.deleteGlacier(testGlacier.getId());
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.NO_CONTENT, response.getStatusCode());
        
        verify(glacierService).findById(testGlacier.getId());
        verify(glacierService).deleteById(testGlacier.getId());
    }
    
    @Test
    void testDeleteGlacier_NotFound() {
        // Given
        UUID nonExistentId = UUID.randomUUID();
        when(glacierService.findById(nonExistentId))
            .thenReturn(Optional.empty());
        
        // When
        ResponseEntity<Void> response = 
            glacierController.deleteGlacier(nonExistentId);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.NOT_FOUND, response.getStatusCode());
        
        verify(glacierService).findById(nonExistentId);
        verify(glacierService, never()).deleteById(any(UUID.class));
    }
    
    @Test
    void testSearchGlaciers() {
        // Given
        String searchTerm = "Test";
        Pageable pageable = PageRequest.of(0, 10);
        Page<Glacier> glacierPage = new PageImpl<>(Arrays.asList(testGlacier), pageable, 1);
        
        when(glacierService.searchByName(searchTerm, pageable))
            .thenReturn(glacierPage);
        
        // When
        ResponseEntity<PageResponse<GlacierDto>> response = 
            glacierController.searchGlaciers(searchTerm, pageable);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(1, response.getBody().getContent().size());
        
        verify(glacierService).searchByName(searchTerm, pageable);
    }
    
    @Test
    void testGetGlaciersByRegion() {
        // Given
        String region = "Central Asia";
        List<Glacier> glaciers = Arrays.asList(testGlacier);
        
        when(glacierService.findByRegion(region))
            .thenReturn(glaciers);
        
        // When
        ResponseEntity<List<GlacierDto>> response = 
            glacierController.getGlaciersByRegion(region);
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(1, response.getBody().size());
        assertEquals("Central Asia", response.getBody().get(0).getRegion());
        
        verify(glacierService).findByRegion(region);
    }
    
    @Test
    void testGetGlacierStatistics() {
        // Given
        when(glacierService.getStatistics()).thenReturn(
            new Object[]{
                100L,        // total count
                500.0,       // total area
                1500.0,      // total length
                3650.0,      // avg elevation
                2000.0,      // min elevation
                5000.0       // max elevation
            }
        );
        
        // When
        ResponseEntity<Object[]> response = 
            glacierController.getGlacierStatistics();
        
        // Then
        assertNotNull(response);
        assertEquals(HttpStatus.OK, response.getStatusCode());
        assertNotNull(response.getBody());
        assertEquals(6, response.getBody().length);
        assertEquals(100L, response.getBody()[0]);
        
        verify(glacierService).getStatistics();
    }
}