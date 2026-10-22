// horizontal bar chart of the most reported issue categories (HVAC, Plumbing, ...) in the selected range.
// answers "what are the most common issue categories?". renders period.by_category from GET /analytics/dashboard
// (CountItem[], already sorted largest first by the backend). shown on the Facility Admin and Engineer dashboards
import { useTheme } from '@mui/material/styles';
import { BarChart } from '@mui/x-charts/BarChart';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';

// the chart grows with the number of categories so bars keep the same thickness
const ROW_HEIGHT = 30;

{/**
 * most common issue categories in the range, largest first. clicking a bar opens those incidents
 *  - items: [{key: category name, count}]
 *  - onSelect(category): called with the clicked bar's category, omit to make bars non-clickable
 */}
function CategoryChart({items, rangeLabel, onSelect}) {
    const theme = useTheme();
    const labels = items.map((item) => item.key);

    return (
        <DashboardCard title="Top issue categories" subtitle={`Reported, ${rangeLabel}`}>
            {items.length ? (
                <BarChart
                    layout="horizontal"
                    // + room for the x axis
                    height={items.length * ROW_HEIGHT + 40}
                    margin={{left: 0, right: 16, top: 8}}
                    yAxis={[{scaleType: 'band', data: labels, width: 'auto', categoryGapRatio: 0.35, disableTicks: true}]}
                    xAxis={[{tickMinStep: 1}]}
                    // one series, so one color: bar length carries the count
                    series={[{data: items.map((item) => item.count), label: 'Incidents', color: theme.palette.chart.primary}]}
                    hideLegend
                    borderRadius={4}
                    grid={{vertical: true}}
                    onItemClick={onSelect ? (event, item) => onSelect(labels[item.dataIndex]) : undefined}
                    sx={onSelect ? {'& .MuiBarElement-root': {cursor: 'pointer'}} : undefined}
                />
            ) : (
                <EmptyState>No tickets reported in this period.</EmptyState>
            )}
        </DashboardCard>
    );
}

export default CategoryChart;
