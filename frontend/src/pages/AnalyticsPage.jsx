import { Paper, Typography } from '@mui/material';

{/** placeholder until the reporting endpoints exist (ticket counts by status/priority/assignee, etc.) */}
function AnalyticsPage() {
    return (
        <Paper variant="outlined" sx={{p: 4}}>
            <Typography variant="h6" component="h2" gutterBottom>Analytics</Typography>
            <Typography color="text.secondary">
                Ticket counts by status, priority and assignee, resolution times and recurring
                issues by location will show up here.
            </Typography>
        </Paper>
    );
}

export default AnalyticsPage;
