import { Box, Card, CardActionArea, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import Delta from './Delta.jsx';

{/**
 * one headline number
 *  - tone: MUI palette key for the icon (status meaning, e.g. 'error' for blocked). dropped when muted
 *  - muted: grey the tile out, e.g. "0 blocked" shouldn't look alarming
 *  - delta: props for <Delta> (change vs the previous period)
 *  - onClick: makes the whole tile a link (drill-down)
 */}
function StatCard({label, value, icon: Icon, tone = 'primary', muted = false, caption, delta, onClick}) {
    const content = (
        <Box sx={{p: 2, height: '100%', display: 'flex', flexDirection: 'column', gap: 0.5}}>
            <Stack direction="row" spacing={1} sx={{alignItems: 'center'}}>
                <Typography variant="body2" color="text.secondary" sx={{flex: 1, fontWeight: 500}}>
                    {label}
                </Typography>
                {Icon && (
                    <Box
                        sx={(theme) => {
                            const color = muted ? theme.palette.text.disabled : theme.palette[tone].main;
                            return {
                                display: 'grid', placeItems: 'center', width: 32, height: 32, borderRadius: 2,
                                color, bgcolor: alpha(color, 0.12),
                            };
                        }}
                    >
                        <Icon fontSize="small" />
                    </Box>
                )}
            </Stack>
            <Stack direction="row" spacing={0.5} sx={{alignItems: 'baseline'}}>
                <Typography variant="h4" component="p" sx={{fontWeight: 700, color: muted ? 'text.secondary' : 'text.primary'}}>
                    {value}
                </Typography>
                {onClick && <ChevronRightIcon fontSize="small" sx={{color: 'text.disabled', alignSelf: 'center'}} />}
            </Stack>
            {caption && <Typography variant="body2" color="text.secondary">{caption}</Typography>}
            {delta && <Delta {...delta} />}
        </Box>
    );

    return (
        <Card sx={{height: '100%'}}>
            {onClick ? <CardActionArea onClick={onClick} sx={{height: '100%'}}>{content}</CardActionArea> : content}
        </Card>
    );
}

export default StatCard;
