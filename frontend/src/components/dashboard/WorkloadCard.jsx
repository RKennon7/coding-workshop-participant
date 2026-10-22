// "Engineer workload": each engineer's availability and open tickets against their capacity, busiest first,
// with warnings for stranded and overloaded engineers. answers "which engineers are available, and how is work spread?".
// renders workload (EngineerLoad[]) from GET /analytics/dashboard. Facility Admins see every engineer in their chosen
// facilities (rows link to that engineer's tickets); engineers see their own facility's team, with their own row highlighted
import { Alert, Avatar, Box, LinearProgress, List, ListItem, ListItemButton, Stack, Typography } from '@mui/material';
import CircleIcon from '@mui/icons-material/Circle';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';
import { loadTone } from './dashboardMeta.js';

// "Dana Lee" -> "DL", for the avatar
const initials = (name) => name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2).toUpperCase();

/**
 * One engineer: avatar, name + availability, specialty and counts, and a capacity bar.
 *  - engineer: an EngineerLoad from the API
 *  - facilityName: shown before the specialty when the list spans several facilities
 */
function EngineerRow({engineer, rangeLabel, facilityName}) {
    const tone = loadTone(engineer.load_pct);
    // zero counts are left out (filter(Boolean)); resolved is always shown
    const extras = [
        engineer.blocked && `${engineer.blocked} blocked`,
        engineer.critical_or_high && `${engineer.critical_or_high} critical/high`,
        `${engineer.resolved_in_range} resolved ${rangeLabel}`,
    ].filter(Boolean);

    return (
        <Box sx={{display: 'grid', gridTemplateColumns: {xs: 'auto 1fr', sm: 'auto minmax(0, 1fr) minmax(140px, 220px)'}, gap: 1.5, alignItems: 'center', width: '100%'}}>
            <Avatar sx={{width: 36, height: 36, fontSize: 14, bgcolor: 'action.selected', color: 'text.primary'}}>
                {initials(engineer.display_name)}
            </Avatar>
            <Box sx={{minWidth: 0}}>
                <Stack direction="row" spacing={1} sx={{alignItems: 'center'}}>
                    <Typography variant="body2" noWrap sx={{fontWeight: 600}}>{engineer.display_name}</Typography>
                    <Stack direction="row" spacing={0.5} sx={{alignItems: 'center', color: engineer.is_available ? 'success.main' : 'text.disabled'}}>{/* availability: a colored dot plus the word, never color alone */}
                        <CircleIcon sx={{fontSize: 8}} />
                        <Typography variant="caption" color="text.secondary">{engineer.is_available ? 'Available' : 'Unavailable'}</Typography>
                    </Stack>
                </Stack>
                <Typography variant="caption" color="text.secondary" component="p" noWrap>
                    {facilityName && `${facilityName} · `}{engineer.specialty ?? 'Generalist'} · {extras.join(' · ')}
                </Typography>
            </Box>
            {/* capacity: open tickets against the engineer's max, labelled so it doesn't rely on color */}
            <Box sx={{gridColumn: {xs: '1 / -1', sm: 'auto'}}}>
                <Stack direction="row" sx={{justifyContent: 'space-between'}}>
                    <Typography variant="caption" color="text.secondary">Capacity</Typography>
                    <Typography variant="caption" sx={{fontWeight: 600}}>
                        {engineer.active} / {engineer.max_open_tickets} open
                    </Typography>
                </Stack>
                <LinearProgress
                    variant="determinate"
                    // the bar stops at full; the label above still shows the real count when over capacity
                    value={Math.min(100, engineer.load_pct)}
                    color={tone}
                    sx={{height: 6, borderRadius: 3, bgcolor: 'action.hover'}}
                    aria-label={`${engineer.display_name} capacity`}
                />
            </Box>
        </Box>
    );
}

{/**
 * engineer availability + how open work is spread across the team, busiest first.
 * onSelect(engineer) makes a row clickable (admins drill into that engineer's tickets)
 * facilityNames: {id: name}, pass it when the list spans several facilities to label each engineer
 * highlightUserId: shades that engineer's row (an engineer's own row on their dashboard)
 * engineers: data.workload, already sorted busiest first (by load_pct) by the backend
 */}
function WorkloadCard({engineers, rangeLabel, onSelect, highlightUserId, facilityNames}) {
    const available = engineers.filter((e) => e.is_available);
    const totalActive = engineers.reduce((sum, e) => sum + e.active, 0);
    // tickets sitting with someone who can't work on them right now
    const stranded = engineers.filter((e) => !e.is_available && e.active > 0);
    // same 100% line as loadTone's 'error'
    const overloaded = engineers.filter((e) => e.load_pct >= 100);

    return (
        <DashboardCard
            title="Engineer workload"
            subtitle={`${totalActive} active ticket${totalActive === 1 ? '' : 's'} across ${available.length} of ${engineers.length} engineers available`}
        >
            {stranded.map((e) => (
                <Alert key={e.user_id} severity="warning" sx={{mb: 1}}>
                    {e.display_name} is unavailable but still has {e.active} open ticket{e.active === 1 ? '' : 's'}. Consider reassigning.
                </Alert>
            ))}
            {overloaded.length > 0 && (
                <Alert severity="error" sx={{mb: 1}}>
                    At or over capacity: {overloaded.map((e) => e.display_name).join(', ')}
                </Alert>
            )}
            {engineers.length === 0 ? (
                <EmptyState>No engineer profiles yet.</EmptyState>
            ) : (
                <List dense disablePadding sx={{mx: -1}}>
                    {engineers.map((engineer) => {
                        const highlighted = engineer.user_id === highlightUserId;
                        const sx = {px: 1, py: 1, borderRadius: 2, ...(highlighted && {bgcolor: 'action.selected'})};
                        return onSelect ? (
                            <ListItemButton key={engineer.user_id} onClick={() => onSelect(engineer)} sx={sx}>
                                <EngineerRow engineer={engineer} rangeLabel={rangeLabel} facilityName={facilityNames?.[engineer.facility_id]} />
                            </ListItemButton>
                        ) : (
                            <ListItem key={engineer.user_id} sx={sx}>
                                <EngineerRow engineer={engineer} rangeLabel={rangeLabel} facilityName={facilityNames?.[engineer.facility_id]} />
                            </ListItem>
                        );
                    })}
                </List>
            )}
        </DashboardCard>
    );
}

export default WorkloadCard;
