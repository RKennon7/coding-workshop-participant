// read-only status audit trail for one incident, rendered under the fields of the incident edit/view form
// (IncidentsPage passes it to ResourceView's renderFormExtras). every role that can open the ticket sees it;
// the backend returns 404 for tickets the user isn't allowed to see.
import { useEffect, useState } from 'react';
import { Alert, Box, Chip, Divider, Stack, Typography } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import EnumChip from '../common/EnumChip.jsx';
import { fetchIncidentHistory } from '../../services/index.js';
import { getErrorMessage } from '../../hooks/useResource.js';
import { INCIDENT_STATUSES, STATUS_COLORS } from '../../constants/enums.js';
import { formatDateTime } from '../../utils/format.js';

{/**
 * Workflow strip (where the ticket is now) + timeline of every status change, shown inside the incident form.
 *  - incidentId: loads GET /incidents/{id}/history (oldest first) once per incident
 *  - currentStatus: the status highlighted in the workflow strip
 * the strip just lists the statuses in order, it doesn't show which transitions are allowed
 * (see auth/incidentRules.js for that). the history isn't refetched after a save, but the form
 * closes on save, and reopening it mounts a fresh copy.
 */}
function IncidentHistory({incidentId, currentStatus}) {
    const [history, setHistory] = useState([]);
    const [error, setError] = useState(null);

    // cancelled: ignore a response that arrives after the form closed or switched to another incident
    useEffect(() => {
        let cancelled = false;
        fetchIncidentHistory(incidentId)
            .then((rows) => !cancelled && setHistory(rows))
            .catch((err) => !cancelled && setError(getErrorMessage(err)));
        return () => { cancelled = true; };
    }, [incidentId]);

    return (
        <Box>
            <Divider sx={{mb: 2}} />
            <Typography variant="subtitle1" gutterBottom>Workflow</Typography>
            <Stack direction="row" spacing={0.5} useFlexGap sx={{alignItems: 'center', flexWrap: 'wrap', mb: 2}}>
                {INCIDENT_STATUSES.map((status, index) => (
                    <Stack key={status} direction="row" spacing={0.5} sx={{alignItems: 'center'}}>
                        {index > 0 && <ArrowForwardIcon fontSize="inherit" color="disabled" />}
                        <Chip
                            label={status}
                            size="small"
                            color={status === currentStatus ? (STATUS_COLORS[status] ?? 'default') : 'default'}
                            variant={status === currentStatus ? 'filled' : 'outlined'}
                        />
                    </Stack>
                ))}
            </Stack>

            {error && <Alert severity="error" sx={{mb: 1}}>{error}</Alert>}
            <Stack spacing={1}>
                {history.map((entry) => (
                    <Box key={entry.id} sx={{display: 'flex', gap: 1, alignItems: 'baseline', flexWrap: 'wrap'}}>
                        <Typography variant="caption" color="text.secondary" sx={{minWidth: 150}}>
                            {formatDateTime(entry.changed_at)}
                        </Typography>
                        {/* the first entry is the ticket's creation: it has no from_status */}
                        {entry.from_status ? (
                            <>
                                <EnumChip value={entry.from_status} colors={STATUS_COLORS} />
                                <ArrowForwardIcon fontSize="inherit" color="disabled" />
                                <EnumChip value={entry.to_status} colors={STATUS_COLORS} />
                            </>
                        ) : (
                            <Typography variant="body2">Reported</Typography>
                        )}
                        <Typography variant="body2" color="text.secondary">by {entry.changed_by.username}</Typography>
                        {/* only set on moves to Blocked: the backend copies the (required) blocked_reason into the history row */}
                        {entry.reason && (
                            <Typography variant="body2" sx={{width: '100%', pl: {sm: '158px'}}}>
                                Reason: {entry.reason}
                            </Typography>
                        )}
                    </Box>
                ))}
            </Stack>
        </Box>
    );
}

export default IncidentHistory;
