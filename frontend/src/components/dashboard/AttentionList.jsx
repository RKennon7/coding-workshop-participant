import { Avatar, Box, Chip, List, ListItemAvatar, ListItemButton, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import EnumChip from '../common/EnumChip.jsx';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';
import { FLAG_META, formatLocation } from './dashboardMeta.js';
import { PRIORITY_COLORS } from '../../constants/enums.js';
import { formatDuration } from '../../utils/format.js';

function FlagChip({kind}) {
    const {label, color, icon: Icon} = FLAG_META[kind];
    return <Chip size="small" variant="outlined" color={color} icon={<Icon />} label={label} />;
}

function AttentionItem({ticket, onOpen, showAssignee, showFacility}) {
    // flags arrive most urgent first: the first one picks the icon and gives the headline reason
    const [primary, ...others] = ticket.flags;
    const meta = FLAG_META[primary.kind];
    const Icon = meta.icon;
    const people = showAssignee
        ? (ticket.assignee ? `Assigned to ${ticket.assignee.username}` : 'No assignee')
        : `Reported by ${ticket.reporter.username}`;

    return (
        <ListItemButton alignItems="flex-start" onClick={() => onOpen(ticket.id)} sx={{px: 1, borderRadius: 2}}>
            <ListItemAvatar sx={{minWidth: 48}}>
                <Avatar
                    sx={(theme) => ({
                        width: 36, height: 36,
                        color: theme.palette[meta.color].main,
                        bgcolor: alpha(theme.palette[meta.color].main, 0.12),
                    })}
                >
                    <Icon fontSize="small" />
                </Avatar>
            </ListItemAvatar>
            <Box sx={{minWidth: 0, flex: 1}}>
                <Stack direction="row" spacing={1} sx={{alignItems: 'center', minWidth: 0}}>
                    <Typography variant="body2" noWrap sx={{fontWeight: 600, minWidth: 0}}>
                        #{ticket.id} {ticket.title}
                    </Typography>
                    <EnumChip value={ticket.priority} colors={PRIORITY_COLORS} />
                </Stack>
                {/* the "why": blocked/escalation reason, SLA overrun, how long it's been waiting */}
                <Typography variant="body2" sx={{mt: 0.25}}>
                    <Box component="span" sx={{fontWeight: 600, color: `${meta.color}.main`}}>{meta.label}</Box>
                    {primary.detail && <> · {primary.detail}</>}
                </Typography>
                <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 0.75, alignItems: 'center', mt: 0.75}}>
                    {others.map((flag) => <FlagChip key={flag.kind} kind={flag.kind} />)}
                    <Typography variant="caption" color="text.secondary">
                        {formatLocation(ticket.location, showFacility)} · {people} · {formatDuration(ticket.age_hours)} old
                    </Typography>
                </Stack>
            </Box>
        </ListItemButton>
    );
}

{/**
 * flagged tickets with the reason they need someone, most urgent first.
 * chips on top narrow the list to one kind of problem; clicking a ticket opens it
 */}
function AttentionList({tickets, filter, onFilterChange, onOpen, showAssignee = true, showFacility = false, maxHeight = 460}) {
    const counts = {};
    for (const ticket of tickets) {
        for (const flag of ticket.flags) {
            counts[flag.kind] = (counts[flag.kind] ?? 0) + 1;
        }
    }
    const visible = filter ? tickets.filter((t) => t.flags.some((f) => f.kind === filter)) : tickets;

    return (
        <DashboardCard
            title="Needs attention"
            subtitle={tickets.length ? `${tickets.length} ticket${tickets.length === 1 ? '' : 's'} flagged, most urgent first` : 'Nothing flagged right now'}
        >
            {tickets.length > 0 && (
                <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 0.75, mb: 1}}>
                    <Chip
                        size="small"
                        label={`All ${tickets.length}`}
                        color={filter ? 'default' : 'primary'}
                        variant={filter ? 'outlined' : 'filled'}
                        onClick={() => onFilterChange(null)}
                    />
                    {Object.entries(FLAG_META).filter(([kind]) => counts[kind]).map(([kind, {label, icon: Icon}]) => (
                        <Chip
                            key={kind}
                            size="small"
                            icon={<Icon />}
                            label={`${label} ${counts[kind]}`}
                            color={filter === kind ? 'primary' : 'default'}
                            variant={filter === kind ? 'filled' : 'outlined'}
                            onClick={() => onFilterChange(filter === kind ? null : kind)}
                        />
                    ))}
                </Stack>
            )}
            {visible.length === 0 ? (
                <EmptyState>{tickets.length ? 'No tickets with this flag.' : 'No blocked, escalated, overdue or forgotten tickets.'}</EmptyState>
            ) : (
                <List dense disablePadding sx={{maxHeight, overflowY: 'auto', mx: -1}}>
                    {visible.map((ticket) => (
                        <AttentionItem key={ticket.id} ticket={ticket} onOpen={onOpen} showAssignee={showAssignee} showFacility={showFacility} />
                    ))}
                </List>
            )}
        </DashboardCard>
    );
}

export default AttentionList;
