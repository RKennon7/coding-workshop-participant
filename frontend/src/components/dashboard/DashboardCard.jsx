// the shared card frame every dashboard section sits in (title, optional subtitle and top-right action),
// plus EmptyState for sections with no data. pure layout: renders no /analytics data itself. used on all roles' dashboards
import { Box, Card, Stack, Typography } from '@mui/material';

{/** titled panel for one dashboard section. action sits top-right (e.g. a toggle) and wraps under the title on narrow cards */}
function DashboardCard({title, subtitle, action, children, sx}) {
    return (
        <Card sx={{height: '100%', display: 'flex', flexDirection: 'column', ...sx}}>
            <Stack direction="row" useFlexGap sx={{alignItems: 'flex-start', flexWrap: 'wrap', gap: 1, px: 2.5, pt: 2, pb: 1.5}}>
                <Box sx={{flex: '1 1 160px', minWidth: 0}}>
                    <Typography variant="subtitle1" component="h3" sx={{fontWeight: 600}}>{title}</Typography>
                    {subtitle && <Typography variant="body2" color="text.secondary">{subtitle}</Typography>}
                </Box>
                {action}
            </Stack>
            <Box sx={{px: 2.5, pb: 2, flex: 1, minWidth: 0}}>{children}</Box>
        </Card>
    );
}

// centered grey text for a section with nothing to show
export function EmptyState({children}) {
    return (
        <Box sx={{py: 4, textAlign: 'center'}}>
            <Typography variant="body2" color="text.secondary">{children}</Typography>
        </Box>
    );
}

export default DashboardCard;
