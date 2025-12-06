package com.example.reports.api.dto;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.LocalDate;

@Data
@AllArgsConstructor
public class DailyReportDto {
    private LocalDate eventDate;
    private long prosthesisId;
    private long sessionsCount;
    private double avgReactionMs;
    private double batteryAvgLevel;
    private long errorsCount;
}