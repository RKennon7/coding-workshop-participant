import { Stack, Typography } from '@mui/material';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import RemoveIcon from '@mui/icons-material/Remove';

{/**
 * change vs the previous period, e.g. "▼ 2.7h vs previous 30 days"
 *  - lowerIsBetter: for durations, a drop is good news (green)
 *  - format: how to show the size of the change (defaults to the plain number)
 *  - compareTo: what the previous period is called, nothing renders without it
 */}
function Delta({current, previous, lowerIsBetter = false, format = (value) => value, compareTo}) {
    if (current == null || previous == null || !compareTo) {
        return null;
    }
    const diff = current - previous;
    const flat = Math.abs(diff) < 0.05;
    const improved = lowerIsBetter ? diff < 0 : diff > 0;
    const color = flat ? 'text.secondary' : improved ? 'success.main' : 'error.main';
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
