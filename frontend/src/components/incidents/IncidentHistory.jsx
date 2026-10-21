import { useEffect, useState } from 'react';
import { Alert, Box, Chip, Divider, Stack, Typography } from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import EnumChip from '../common/EnumChip.jsx';
import { fetchIncidentHistory } from '../../services/index.js';
import { getErrorMessage } from '../../hooks/useResource.js';
import { INCIDENT_STATUSES, STATUS_COLORS } from '../../constants/enums.js';
import { formatDateTime } from '../../utils/format.js';

{/** workflow strip (where the ticket is now) + timeline of every status change, shown inside the incident form */}
function IncidentHistory({incidentId, currentStatus}) {
    const [history, setHistory] = useState([]);
    const [error, setError] = useState(null);

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
            <Stack direction="row" spacing={0.5} alignItems="center" useFlexGap flexWrap="wrap" sx={{mb: 2}}>
                {INCIDENT_STATUSES.map((status, index) => (
                    <Stack key={status} direction="row" spacing={0.5} alignItems="center">
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
