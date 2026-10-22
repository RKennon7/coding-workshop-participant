import { useTheme } from '@mui/material/styles';
import { BarChart } from '@mui/x-charts/BarChart';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';
import { formatShortDate } from '../../utils/format.js';

const MAX_TICK_LABELS = 6;

{/** tickets reported vs resolved per day (or week, for long ranges): is the backlog growing or shrinking? */}
function TrendChart({period, rangeLabel}) {
    const theme = useTheme();
    const points = period.trend;
    const weekly = period.trend_bucket === 'week';
    const hasData = points.some((p) => p.created || p.resolved);
    // band axis labels every bucket, so thin them out to keep long ranges readable
    const labelStep = Math.max(1, Math.ceil(points.length / MAX_TICK_LABELS));

    return (
        <DashboardCard
            title="Reported vs resolved"
            subtitle={`${period.created} reported · ${period.resolved} resolved, ${rangeLabel}${weekly ? ' (per week)' : ''}`}
        >
            {hasData ? (
                <BarChart
                    height={260}
                    margin={{left: 0, right: 8}}
                    xAxis={[{
                        scaleType: 'band',
                        data: points.map((p) => new Date(p.bucket)),
                        valueFormatter: (date, context) => (
                            context.location === 'tooltip' && weekly ? `Week of ${formatShortDate(date)}` : formatShortDate(date)
                        ),
                        tickInterval: (_, index) => index % labelStep === 0,
                        categoryGapRatio: 0.3,
                        barGapRatio: 0.1,
                        disableTicks: true,
                    }]}
                    yAxis={[{tickMinStep: 1, width: 'auto'}]}
                    // grouped side by side per bucket: a taller "Reported" bar means the backlog grew that day
                    series={[
                        {data: points.map((p) => p.created), label: 'Reported', color: theme.palette.chart.primary},
                        {data: points.map((p) => p.resolved), label: 'Resolved', color: theme.palette.chart.secondary},
                    ]}
                    borderRadius={3}
                    grid={{horizontal: true}}
                />
            ) : (
                <EmptyState>No tickets reported or resolved in this period.</EmptyState>
            )}
        </DashboardCard>
    );
}

export default TrendChart;
