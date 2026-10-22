// small "better / worse vs the previous period" line under a number, e.g. "▼ 2.7h better vs previous 30 days".
// answers "is this getting better or worse?" for the speed tiles and the SLA card (Admin + Engineer dashboards).
// the previous values come from the /analytics/dashboard response (Duration.previous_median_hours,
// SlaStats.previous_met_pct), measured over the same-length window right before the selected range
import { Stack, Typography } from '@mui/material';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import RemoveIcon from '@mui/icons-material/Remove';

{/**
 * change vs the previous period, e.g. "▼ 2.7h vs previous 30 days"
 *  - lowerIsBetter: for durations, a drop is good news (green)
 *  - format: how to show the size of the change (defaults to the plain number)
 *  - compareTo: what the previous period is called, nothing renders without it
 *    (null for "all time", see describePreviousRange in hooks/useDashboard.js)
 *  - current / previous: the two values in the same unit (hours, percent). nothing renders if either is missing
 */}
function Delta({current, previous, lowerIsBetter = false, format = (value) => value, compareTo}) {
    if (current == null || previous == null || !compareTo) {
        return null;
    }
    const diff = current - previous;
    // tiny differences (rounding noise) read as "No change" rather than a trend
    const flat = Math.abs(diff) < 0.05;
    const improved = lowerIsBetter ? diff < 0 : diff > 0;
    const color = flat ? 'text.secondary' : improved ? 'success.main' : 'error.main';
    // the arrow shows which way the number moved; color plus the words "better"/"worse" say whether that's good,
    // so the meaning never relies on color alone
    const Icon = flat ? RemoveIcon : diff < 0 ? ArrowDownwardIcon : ArrowUpwardIcon;

    return (
        <Stack direction="row" spacing={0.5} sx={{alignItems: 'center'}}>
            <Icon sx={{fontSize: 16, color}} />
            <Typography variant="caption" color="text.secondary">
                {flat ? 'No change' : <><Typography component="span" variant="caption" sx={{fontWeight: 600, color}}>{format(Math.abs(diff))}</Typography>{improved ? ' better' : ' worse'}</>}
                {' '}vs {compareTo}
            </Typography>
        </Stack>
    );
}

export default Delta;
