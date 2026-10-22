// "Needs attention": flagged tickets with the reason each one needs someone, most urgent first.
// answers "which incidents are escalated, blocked, overdue or forgotten, and why?". unlike the other cards it
// fetches its own data, a page at a time, from GET /analytics/attention (AttentionPage in backend/v1/app/schemas/analytics.py).
// shown on the Facility Admin and Engineer dashboards
import { useEffect, useState } from 'react';
import { Alert, Avatar, Box, Chip, LinearProgress, List, ListItemAvatar, ListItemButton, Pagination, Stack, Typography } from '@mui/material';
import { alpha } from '@mui/material/styles';
import EnumChip from '../common/EnumChip.jsx';
import DashboardCard, { EmptyState } from './DashboardCard.jsx';
import { FLAG_META, formatLocation } from './dashboardMeta.js';
import { PRIORITY_COLORS } from '../../constants/enums.js';
import { formatDuration } from '../../utils/format.js';
import { fetchAttention } from '../../services/index.js';
import { getErrorMessage } from '../../hooks/useResource.js';

const PAGE_SIZE = 5;

/** one secondary flag as a small outlined chip: icon + label, never color alone */
function FlagChip({kind}) {
    const {label, color, icon: Icon} = FLAG_META[kind];
    return <Chip size="small" variant="outlined" color={color} icon={<Icon />} label={label} />;
}

/**
 * One flagged ticket row.
 *  - ticket: a TicketSummary from the API, with at least one flag (the backend only returns flagged tickets)
 *  - showAssignee: admins see who it's assigned to; engineers (whose ticket it is) see the reporter instead
 *  - showFacility: prefix the location with the campus when several are on screen
 */
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
 * flagged tickets with the reason they need someone, most urgent first, a page at a time (GET /analytics/attention).
 * chips on top narrow the list to one kind of problem (their counts cover every flagged ticket); clicking a ticket opens it
 *  - scope: {facility_id, building_id}, the dashboard's filters
 *  - refreshKey: changes whenever the dashboard reloads, so the list reloads with it
 */}
function AttentionList({scope, refreshKey, filter, onFilterChange, onOpen, showAssignee = true, showFacility = false, pageSize = PAGE_SIZE}) {
    // back to the first page whenever the filter or the dashboard's scope changes
    // the page is stored together with the key it belongs to, so a new key reads as page 0 without an extra effect
    const listKey = JSON.stringify({scope, filter});
    const [pageState, setPageState] = useState({listKey, page: 0});
    const page = pageState.listKey === listKey ? pageState.page : 0;

    const requestKey = JSON.stringify({listKey, page, refreshKey});
    // result remembers which request it answers: loading is derived from that, and the previous page stays visible meanwhile
    const [result, setResult] = useState({key: null, data: null, error: null});
    useEffect(() => {
        let cancelled = false;
        fetchAttention({...scope, kind: filter ?? undefined, limit: pageSize, offset: page * pageSize})
            .then((data) => !cancelled && setResult({key: requestKey, data, error: null}))
            // on error keep the last page on screen and show the message above it
            .catch((err) => !cancelled && setResult((prev) => ({...prev, key: requestKey, error: getErrorMessage(err)})));
        return () => {
            cancelled = true;
        };
        // requestKey covers scope/filter/page/refreshKey
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [requestKey]);

    const {data, error} = result;
    const loading = result.key !== requestKey;
    // counts cover every flagged ticket in scope (for the subtitle and chips); data.total only those matching the filter (for paging)
    const flagged = data?.counts.total ?? 0;
    const pages = data ? Math.ceil(data.total / pageSize) : 0;
    const first = page * pageSize + 1;

    return (
        <DashboardCard
            title="Needs attention"
            subtitle={!data ? 'Loading…' : flagged ? `${flagged} ticket${flagged === 1 ? '' : 's'} flagged, most urgent first` : 'Nothing flagged right now'}
        >
            {error && <Alert severity="error" sx={{mb: 1}}>{error}</Alert>}
            {flagged > 0 && (
                <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 0.75, mb: 1}}>
                    <Chip
                        size="small"
                        label={`All ${flagged}`}
                        color={filter ? 'default' : 'primary'}
                        variant={filter ? 'outlined' : 'filled'}
                        onClick={() => onFilterChange(null)}
                    />
                    {Object.entries(FLAG_META).filter(([kind]) => data.counts.by_kind[kind]).map(([kind, {label, icon: Icon}]) => (
                        <Chip
                            // one chip per flag kind that has tickets, in urgency order. clicking the selected chip clears the filter
                            key={kind}
                            size="small"
                            icon={<Icon />}
                            label={`${label} ${data.counts.by_kind[kind]}`}
                            color={filter === kind ? 'primary' : 'default'}
                            variant={filter === kind ? 'filled' : 'outlined'}
                            onClick={() => onFilterChange(filter === kind ? null : kind)}
                        />
                    ))}
                </Stack>
            )}
            {loading && <LinearProgress sx={{height: 2, mb: 1}} />}
            {data && data.items.length === 0 ? (
                <EmptyState>{flagged ? 'No tickets with this flag.' : 'No blocked, escalated, overdue or forgotten tickets.'}</EmptyState>
            ) : (
                <List dense disablePadding sx={{mx: -1, opacity: loading ? 0.6 : 1}}>
                    {data?.items.map((ticket) => (
                        <AttentionItem key={ticket.id} ticket={ticket} onOpen={onOpen} showAssignee={showAssignee} showFacility={showFacility} />
                    ))}
                </List>
            )}
            {pages > 1 && (
                <Stack direction="row" sx={{alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1, mt: 1}}>
                    <Typography variant="caption" color="text.secondary">
                        {first}–{Math.min(first + pageSize - 1, data.total)} of {data.total}
                    </Typography>
                    <Pagination
                        size="small"
                        count={pages}
                        page={page + 1}
                        onChange={(_, next) => setPageState({listKey, page: next - 1})}
                        siblingCount={0}
                    />
                </Stack>
            )}
        </DashboardCard>
    );
}

export default AttentionList;
