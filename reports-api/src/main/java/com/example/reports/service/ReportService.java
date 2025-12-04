package com.example.reports.service;

import com.example.reports.api.dto.DailyReportDto;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.List;

@Service
@RequiredArgsConstructor
public class ReportService {

    private final JdbcTemplate clickHouseJdbcTemplate;

    public List<DailyReportDto> getDailyReportsForUser(long userId) {
        String sql = """
            SELECT
                event_date,
                prosthesis_id,
                sessions_count,
                avg_reaction_ms,
                battery_avg_level,
                errors_count
            FROM report_prosthesis_daily_stats
            WHERE user_id = ?
            ORDER BY event_date DESC
            LIMIT 30
            """;

        return clickHouseJdbcTemplate.query(
                sql,
                (rs, rowNum) -> mapRow(rs),
                userId
        );
    }

    private DailyReportDto mapRow(ResultSet rs) throws SQLException {
        LocalDate date = rs.getDate("event_date").toLocalDate();
        long prosthesisId = rs.getLong("prosthesis_id");
        long sessionsCount = rs.getLong("sessions_count");
        double avgReactionMs = rs.getDouble("avg_reaction_ms");
        double batteryAvgLevel = rs.getDouble("battery_avg_level");
        long errorsCount = rs.getLong("errors_count");

        return new DailyReportDto(
                date,
                prosthesisId,
                sessionsCount,
                avgReactionMs,
                batteryAvgLevel,
                errorsCount
        );
    }
}