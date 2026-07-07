package kz.glacier.util;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.time.temporal.ChronoUnit;
import java.util.Date;

public final class DateUtils {
    
    public static final ZoneId KAZAKHSTAN_ZONE = ZoneId.of("Asia/Almaty");
    public static final ZoneId UTC_ZONE = ZoneId.of("UTC");
    
    private static final DateTimeFormatter ISO_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE_TIME;
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd");
    private static final DateTimeFormatter DATETIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    
    private DateUtils() {
        // Utility class
    }
    
    public static LocalDateTime nowKazakhstan() {
        return LocalDateTime.now(KAZAKHSTAN_ZONE);
    }
    
    public static LocalDateTime nowUtc() {
        return LocalDateTime.now(UTC_ZONE);
    }
    
    public static LocalDateTime toKazakhstan(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.atZone(UTC_ZONE).withZoneSameInstant(KAZAKHSTAN_ZONE).toLocalDateTime();
    }
    
    public static LocalDateTime toUtc(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.atZone(KAZAKHSTAN_ZONE).withZoneSameInstant(UTC_ZONE).toLocalDateTime();
    }
    
    public static String formatIso(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return ISO_FORMATTER.format(dateTime);
    }
    
    public static String formatDate(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return DATE_FORMATTER.format(dateTime);
    }
    
    public static String formatDateTime(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return DATETIME_FORMATTER.format(dateTime);
    }
    
    public static LocalDateTime parseIso(String dateTimeString) {
        if (dateTimeString == null || dateTimeString.isBlank()) return null;
        try {
            return LocalDateTime.parse(dateTimeString, ISO_FORMATTER);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Invalid ISO date time format: " + dateTimeString, e);
        }
    }
    
    public static LocalDate parseDate(String dateString) {
        if (dateString == null || dateString.isBlank()) return null;
        try {
            return LocalDate.parse(dateString, DATE_FORMATTER);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Invalid date format: " + dateString, e);
        }
    }
    
    public static LocalDateTime parseDateTime(String dateTimeString) {
        if (dateTimeString == null || dateTimeString.isBlank()) return null;
        try {
            return LocalDateTime.parse(dateTimeString, DATETIME_FORMATTER);
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("Invalid datetime format: " + dateTimeString, e);
        }
    }
    
    public static Date toDate(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return Date.from(dateTime.atZone(UTC_ZONE).toInstant());
    }
    
    public static LocalDateTime fromDate(Date date) {
        if (date == null) return null;
        return date.toInstant().atZone(UTC_ZONE).toLocalDateTime();
    }
    
    public static long daysBetween(LocalDateTime start, LocalDateTime end) {
        if (start == null || end == null) return 0;
        return ChronoUnit.DAYS.between(start.toLocalDate(), end.toLocalDate());
    }
    
    public static long hoursBetween(LocalDateTime start, LocalDateTime end) {
        if (start == null || end == null) return 0;
        return ChronoUnit.HOURS.between(start, end);
    }
    
    public static long minutesBetween(LocalDateTime start, LocalDateTime end) {
        if (start == null || end == null) return 0;
        return ChronoUnit.MINUTES.between(start, end);
    }
    
    public static LocalDateTime plusDays(LocalDateTime dateTime, long days) {
        if (dateTime == null) return null;
        return dateTime.plusDays(days);
    }
    
    public static LocalDateTime plusHours(LocalDateTime dateTime, long hours) {
        if (dateTime == null) return null;
        return dateTime.plusHours(hours);
    }
    
    public static LocalDateTime minusDays(LocalDateTime dateTime, long days) {
        if (dateTime == null) return null;
        return dateTime.minusDays(days);
    }
    
    public static LocalDateTime minusHours(LocalDateTime dateTime, long hours) {
        if (dateTime == null) return null;
        return dateTime.minusHours(hours);
    }
    
    public static boolean isBefore(LocalDateTime dateTime1, LocalDateTime dateTime2) {
        if (dateTime1 == null || dateTime2 == null) return false;
        return dateTime1.isBefore(dateTime2);
    }
    
    public static boolean isAfter(LocalDateTime dateTime1, LocalDateTime dateTime2) {
        if (dateTime1 == null || dateTime2 == null) return false;
        return dateTime1.isAfter(dateTime2);
    }
    
    public static boolean isBetween(LocalDateTime dateTime, LocalDateTime start, LocalDateTime end) {
        if (dateTime == null || start == null || end == null) return false;
        return !dateTime.isBefore(start) && !dateTime.isAfter(end);
    }
    
    public static boolean isToday(LocalDateTime dateTime) {
        if (dateTime == null) return false;
        LocalDate today = LocalDate.now(KAZAKHSTAN_ZONE);
        return today.equals(dateTime.toLocalDate());
    }
    
    public static boolean isYesterday(LocalDateTime dateTime) {
        if (dateTime == null) return false;
        LocalDate yesterday = LocalDate.now(KAZAKHSTAN_ZONE).minusDays(1);
        return yesterday.equals(dateTime.toLocalDate());
    }
    
    public static boolean isThisWeek(LocalDateTime dateTime) {
        if (dateTime == null) return false;
        LocalDate today = LocalDate.now(KAZAKHSTAN_ZONE);
        LocalDate weekStart = today.minusDays(today.getDayOfWeek().getValue() - 1);
        LocalDate weekEnd = weekStart.plusDays(6);
        LocalDate date = dateTime.toLocalDate();
        return !date.isBefore(weekStart) && !date.isAfter(weekEnd);
    }
    
    public static boolean isThisMonth(LocalDateTime dateTime) {
        if (dateTime == null) return false;
        LocalDate today = LocalDate.now(KAZAKHSTAN_ZONE);
        return today.getYear() == dateTime.getYear() && today.getMonthValue() == dateTime.getMonthValue();
    }
    
    public static boolean isThisYear(LocalDateTime dateTime) {
        if (dateTime == null) return false;
        return LocalDate.now(KAZAKHSTAN_ZONE).getYear() == dateTime.getYear();
    }
    
    public static LocalDateTime startOfDay(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.toLocalDate().atStartOfDay();
    }
    
    public static LocalDateTime endOfDay(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.toLocalDate().atTime(LocalTime.MAX);
    }
    
    public static LocalDateTime startOfWeek(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        LocalDate date = dateTime.toLocalDate();
        LocalDate weekStart = date.minusDays(date.getDayOfWeek().getValue() - 1);
        return weekStart.atStartOfDay();
    }
    
    public static LocalDateTime endOfWeek(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        LocalDate date = dateTime.toLocalDate();
        LocalDate weekEnd = date.minusDays(date.getDayOfWeek().getValue() - 1).plusDays(6);
        return weekEnd.atTime(LocalTime.MAX);
    }
    
    public static LocalDateTime startOfMonth(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.withDayOfMonth(1).toLocalDate().atStartOfDay();
    }
    
    public static LocalDateTime endOfMonth(LocalDateTime dateTime) {
        if (dateTime == null) return null;
        return dateTime.withDayOfMonth(dateTime.lengthOfMonth()).toLocalDate().atTime(LocalTime.MAX);
    }
}