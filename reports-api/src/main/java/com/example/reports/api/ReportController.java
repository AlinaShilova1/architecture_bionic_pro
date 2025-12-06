package com.example.reports.api;

import com.example.reports.api.dto.DailyReportDto;
import com.example.reports.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.util.List;

@RestController
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;

    @GetMapping("/reports")
    public ResponseEntity<byte[]> getMyReport(JwtAuthenticationToken auth) {
        // Достаём user_id из токена. Маппер в Keycloak должен его туда положить.
        String userIdClaim = auth.getToken().getClaimAsString("user_id");
        if (userIdClaim == null) {
            throw new IllegalStateException("user_id claim is missing in token");
        }

        long userId = Long.parseLong(userIdClaim);

        // Забираем агрегаты из ClickHouse
        List<DailyReportDto> rows = reportService.getDailyReportsForUser(userId);

        // Собираем CSV для скачивания (соответствует фронтовому download blob)
        StringBuilder sb = new StringBuilder();
        sb.append("event_date,prosthesis_id,sessions_count,avg_reaction_ms,battery_avg_level,errors_count\n");
        for (DailyReportDto row : rows) {
            sb.append(row.getEventDate()).append(',')
                    .append(row.getProsthesisId()).append(',')
                    .append(row.getSessionsCount()).append(',')
                    .append(row.getAvgReactionMs()).append(',')
                    .append(row.getBatteryAvgLevel()).append(',')
                    .append(row.getErrorsCount()).append('\n');
        }

        byte[] bytes = sb.toString().getBytes(StandardCharsets.UTF_8);

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"report.csv\"")
                .contentType(MediaType.parseMediaType("text/csv"))
                .body(bytes);
    }
}