import { useState } from 'react';
import { Box, Chip, List, ListItemButton, Stack, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import RepeatIcon from '@mui/icons-material/Repeat';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';

const LEVELS = [
    {key: 'buildings', label: 'Building', filter: 'building_id'},
    {key: 'floors', label: 'Floor', filter: 'floor_id'},
    {key: 'seats', label: 'Seat', filter: 'seat_id'},
];

{/**
 * locations with the most incidents in the range, by building / floor / seat.
 * "Recurring" = the same kind of issue keeps coming back to that spot
 */}
function HotspotsCard({hotspots, rangeLabel, onSelect}) {
    const [level, setLevel] = useState('floors');
    const {filter} = LEVELS.find((l) => l.key === level);
    const items = hotspots[level];
    const max = Math.max(1, ...items.map((item) => item.count));

    return (
        <DashboardCard
            title="Problem locations"
            subtitle={`Most incidents reported, ${rangeLabel}`}
            action={(
                <ToggleButtonGroup size="small" exclusive value={level} onChange={(_, value) => value && setLevel(value)} aria-label="Location level">
                    {LEVELS.map(({key, label}) => <ToggleButton key={key} value={key} sx={{px: 1.25, py: 0.25}}>{label}</ToggleButton>)}
                </ToggleButtonGroup>
            )}
        >
            {items.length === 0 ? (
                <EmptyState>No incidents with a {LEVELS.find((l) => l.key === level).label.toLowerCase()} in this period.</EmptyState>
            ) : (
                <List dense disablePadding sx={{mx: -1}}>
                    {items.map((item) => (
                        <ListItemButton
                            key={item.id}
                            onClick={() => onSelect({[filter]: item.id, building_id: item.building_id})}
                            sx={{px: 1, py: 0.75, borderRadius: 2, display: 'block'}}
                        >
                            <Stack direction="row" spacing={1} sx={{alignItems: 'baseline'}}>
                                <Typography variant="body2" noWrap sx={{flex: 1, minWidth: 0, fontWeight: 500}}>{item.label}</Typography>
                                <Typography variant="body2" sx={{fontWeight: 700}}>{item.count}</Typography>
                            </Stack>
                            <Box sx={{height: 6, borderRadius: 3, bgcolor: 'action.hover', my: 0.5}}>
                                <Box sx={{height: '100%', width: `${(100 * item.count) / max}%`, borderRadius: 3, bgcolor: 'chart.primary'}} />
                            </Box>
                            <Stack direction="row" useFlexGap sx={{alignItems: 'center', flexWrap: 'wrap', columnGap: 1}}>
                                <Typography variant="caption" color="text.secondary">
                                    Mostly {item.top_category} ({item.top_category_count}) · {item.active} still open
                                </Typography>
                                {item.recurring && (
                                    <Chip
                                        size="small"
                                        variant="outlined"
                                        color="warning"
                                        icon={<RepeatIcon />}
                                        label="Recurring"
                                        sx={{height: 20, '& .MuiChip-label': {px: 0.75}}}
                                    />
                                )}
                            </Stack>
                        </ListItemButton>
                    ))}
                </List>
            )}
        </DashboardCard>
    );
}

export default HotspotsCard;
