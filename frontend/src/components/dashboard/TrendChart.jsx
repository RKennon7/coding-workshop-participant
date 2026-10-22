import { useTheme } from '@mui/material/styles';
import { LineChart } from '@mui/x-charts/LineChart';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';
import { formatShortDate } from '../../utils/format.js';

{/** tickets reported vs resolved per day (or week, for long ranges): is the backlog growing or shrinking? */}
function TrendChart({period, rangeLabel}) {
    const theme = useTheme();
    const points = period.trend;
    const weekly = period.trend_bucket === 'week';
    const hasData = points.some((p) => p.created || p.resolved);

    return (
        <DashboardCard
            title="Reported vs resolved"
            subtitle={`${period.created} reported · ${period.resolved} resolved, ${rangeLabel}${weekly ? ' (per week)' : ''}`}
        >
            {hasData ? (
                <LineChart
                    height={260}
                    margin={{left: 0, right: 8}}
                    xAxis={[{
                        scaleType: 'time',
                        data: points.map((p) => new Date(p.bucket)),
                        valueFormatter: (date, context) => (
                            context.location === 'tooltip' && weekly ? `Week of ${formatShortDate(date)}` : formatShortDate(date)
                        ),
                        tickNumber: 6,
                    }]}
                    yAxis={[{tickMinStep: 1, width: 'auto'}]}
                    series={[
                        {data: points.map((p) => p.created), label: 'Reported', color: theme.palette.chart.primary, showMark: false, curve: 'monotoneX'},
                        {data: points.map((p) => p.resolved), label: 'Resolved', color: theme.palette.chart.secondary, showMark: false, curve: 'monotoneX'},
                    ]}
                    grid={{horizontal: true}}
                    sx={{'& .MuiLineElement-root': {strokeWidth: 2}}}
                />
            ) : (
                <EmptyState>No tickets reported or resolved in this period.</EmptyState>
            )}
        </DashboardCard>
    );
}

export default TrendChart;
