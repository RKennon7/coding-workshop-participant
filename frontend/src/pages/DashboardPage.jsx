import { useMemo, useRef, useState } from 'react';
import { Alert, Box, Button, Grid, LinearProgress, Skeleton, Stack, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import BlockIcon from '@mui/icons-material/Block';
import FlagIcon from '@mui/icons-material/Flag';
import TimerOffIcon from '@mui/icons-material/TimerOff';
import TaskAltIcon from '@mui/icons-material/TaskAlt';
import PriorityHighIcon from '@mui/icons-material/PriorityHigh';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AssignmentIndIcon from '@mui/icons-material/AssignmentInd';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import ForumIcon from '@mui/icons-material/Forum';
import CampaignIcon from '@mui/icons-material/Campaign';
import DashboardToolbar from '../components/dashboard/DashboardToolbar.jsx';
import StatCard from '../components/dashboard/StatCard.jsx';
import AttentionList from '../components/dashboard/AttentionList.jsx';
import SlaCard from '../components/dashboard/SlaCard.jsx';
import TrendChart from '../components/dashboard/TrendChart.jsx';
import CategoryChart from '../components/dashboard/CategoryChart.jsx';
import HotspotsCard from '../components/dashboard/HotspotsCard.jsx';
import WorkloadCard from '../components/dashboard/WorkloadCard.jsx';
import MyTickets from '../components/dashboard/MyTickets.jsx';
import { ACTIVE_STATUSES, successTone } from '../components/dashboard/dashboardMeta.js';
import { ROLES } from '../auth/permissions.js';
import { useAuth } from '../context/AuthContext.jsx';
import { useNavigation } from '../context/NavigationContext.jsx';
import { DEFAULT_RANGE, describePreviousRange, describeRange, useDashboard } from '../hooks/useDashboard.js';
import { usePermissions } from '../hooks/usePermissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { buildingsService, facilitiesService } from '../services/index.js';
import { formatDuration } from '../utils/format.js';

const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

// "All facilities", "ACME HQ Campus", "ACME HQ Campus + ACME West Campus"
function describeFacilities(ids, names) {
    if (!ids.length) return 'All facilities';
    return ids.map((id) => names[id] ?? `Facility #${id}`).join(' + ');
}

// heading above a group of cards. detail is a muted note after the title, e.g. the date range
function SectionLabel({children, detail}) {
    return (
        <Typography variant="subtitle1" component="h3" sx={{fontWeight: 600, mt: 1, mb: -0.5}}>
            {children}
            {detail && <Typography component="span" variant="body2" color="text.secondary"> · {detail}</Typography>}
        </Typography>
    );
}

// median time from report to a milestone, with the change vs the previous period
function speedTile(label, icon, duration, compareTo, caption) {
    return {
        label,
        icon,
        value: formatDuration(duration.median_hours),
        caption: caption ?? (duration.count ? `median of ${plural(duration.count, 'ticket')}` : 'no tickets yet'),
        delta: {current: duration.median_hours, previous: duration.previous_median_hours, lowerIsBetter: true, format: formatDuration, compareTo},
    };
}

function keptInformedTile(communication, onClick) {
    const pct = communication.updated_recently_pct;
    return {
        label: 'Kept informed',
        icon: CampaignIcon,
        value: pct == null ? '–' : `${Math.round(pct)}%`,
        tone: successTone(pct),
        muted: pct == null,
        caption: `of active tickets had an update in the last ${communication.silent_after_days} days`,
        onClick,
    };
}

// a row of stat tiles that wraps 2 / 3 / all-in-one-row as the screen grows
function TileRow({tiles}) {
    const lg = 12 / tiles.length;
    return (
        <Grid container spacing={2}>
            {tiles.map((tile) => (
                <Grid key={tile.label} size={{xs: 6, sm: tiles.length > 4 ? 4 : 6, md: tiles.length === 4 ? 3 : 4, lg}}>
                    <StatCard {...tile} />
                </Grid>
            ))}
        </Grid>
    );
}

// ---------- Facility Admin: the whole operation ----------

function AdminDashboard({data, ctx, attentionRef}) {
    const {current, period, communication} = data;
    const {openIncidents, openIncident, showAttention, attention, rangeLabel, compareTo, showFacility, facilityNames} = ctx;

    return (
        <Stack spacing={2}>
            <SectionLabel>Incidents right now</SectionLabel>
            <TileRow tiles={[
                {
                    label: 'Active tickets', icon: ConfirmationNumberIcon, value: current.active,
                    caption: `${current.by_status.Open} open · ${current.by_status['In Progress']} in progress`,
                    onClick: () => openIncidents({status: ACTIVE_STATUSES}),
                },
                {
                    label: 'Unassigned', icon: PersonOffIcon, tone: 'warning', value: current.unassigned, muted: !current.unassigned,
                    caption: 'waiting for an engineer',
                    onClick: () => openIncidents({status: ACTIVE_STATUSES, unassigned: true}),
                },
                {
                    label: 'Blocked', icon: BlockIcon, tone: 'error', value: current.blocked, muted: !current.blocked,
                    caption: 'reasons in Needs attention',
                    onClick: () => openIncidents({status: ['Blocked']}),
                },
                {
                    label: 'Escalated', icon: FlagIcon, tone: 'warning', value: current.escalated, muted: !current.escalated,
                    caption: 'flagged by reporters',
                    onClick: () => openIncidents({status: ACTIVE_STATUSES, is_escalated: true}),
                },
                {
                    label: 'Past SLA target', icon: TimerOffIcon, tone: 'error', value: current.sla_breached, muted: !current.sla_breached,
                    caption: `${current.sla_at_risk} more at risk`,
                    onClick: () => showAttention('sla_breached'),
                },
                {
                    label: 'Awaiting confirmation', icon: TaskAltIcon, tone: 'success', value: current.awaiting_reporter, muted: !current.awaiting_reporter,
                    caption: 'resolved, awaiting reporter to close',
                    onClick: () => openIncidents({status: ['Resolved']}),
                },
            ]} />

            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 7}} ref={attentionRef} sx={{scrollMarginTop: 16}}>
                    <AttentionList {...attention} onOpen={openIncident} showFacility={showFacility} />
                </Grid>
                <Grid size={{xs: 12, md: 5}}>
                    <SlaCard sla={period.sla} current={current} rangeLabel={rangeLabel} compareTo={compareTo} onShowBreached={() => showAttention('sla_breached')} />
                </Grid>
            </Grid>

            <SectionLabel detail={rangeLabel}>Speed &amp; communication</SectionLabel>
            <TileRow tiles={[
                speedTile('Time to acknowledge', VisibilityIcon, period.timings.acknowledge, compareTo),
                speedTile('Time to assign', AssignmentIndIcon, period.timings.assign, compareTo),
                speedTile('Time to resolve', DoneAllIcon, period.timings.resolve, compareTo),
                keptInformedTile(communication, () => showAttention('silent')),
            ]} />

            <SectionLabel detail={rangeLabel}>Trends</SectionLabel>
            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 7, lg: 8}}>
                    <TrendChart period={period} rangeLabel={rangeLabel} />
                </Grid>
                <Grid size={{xs: 12, md: 5, lg: 4}}>
                    <CategoryChart items={period.by_category} rangeLabel={rangeLabel} onSelect={(category) => openIncidents({category: [category]})} />
                </Grid>
            </Grid>

            <SectionLabel>Team &amp; locations</SectionLabel>
            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 7}}>
                    <WorkloadCard
                        engineers={data.workload}
                        rangeLabel={rangeLabel}
                        facilityNames={showFacility ? facilityNames : null}
                        onSelect={(engineer) => openIncidents({status: ACTIVE_STATUSES, assignee_id: engineer.user_id})}
                    />
                </Grid>
                <Grid size={{xs: 12, md: 5}}>
                    <HotspotsCard hotspots={period.hotspots} rangeLabel={rangeLabel} onSelect={openIncidents} showFacility={showFacility} />
                </Grid>
            </Grid>
        </Stack>
    );
}

// ---------- Engineer: my queue + team capacity ----------

function EngineerDashboard({data, ctx, attentionRef, userId}) {
    const {current, period, communication} = data;
    const {openIncidents, openIncident, showAttention, attention, rangeLabel, compareTo} = ctx;
    const mine = (filters) => openIncidents({assignee_id: userId, ...filters});

    return (
        <Stack spacing={2}>
            <SectionLabel>My assigned incidents right now</SectionLabel>
            <TileRow tiles={[
                {
                    label: 'Assigned to me', icon: ConfirmationNumberIcon, value: current.active,
                    caption: `${current.by_status.Open} open · ${current.by_status['In Progress']} in progress`,
                    onClick: () => mine({status: ACTIVE_STATUSES}),
                },
                {
                    label: 'Critical / High', icon: PriorityHighIcon, tone: 'warning', value: current.critical_or_high, muted: !current.critical_or_high,
                    caption: 'work these first',
                    onClick: () => mine({status: ACTIVE_STATUSES, priority: ['Critical', 'High']}),
                },
                {
                    label: 'Blocked', icon: BlockIcon, tone: 'error', value: current.blocked, muted: !current.blocked,
                    caption: 'keep the reason up to date',
                    onClick: () => mine({status: ['Blocked']}),
                },
                {
                    label: 'Past SLA target', icon: TimerOffIcon, tone: 'error', value: current.sla_breached, muted: !current.sla_breached,
                    caption: `${current.sla_at_risk} more at risk`,
                    onClick: () => showAttention('sla_breached'),
                },
                {
                    label: 'Awaiting reporter', icon: TaskAltIcon, tone: 'success', value: current.awaiting_reporter, muted: !current.awaiting_reporter,
                    caption: 'resolved, reporter to confirm',
                    onClick: () => mine({status: ['Resolved']}),
                },
            ]} />

            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 7}} ref={attentionRef} sx={{scrollMarginTop: 16}}>
                    <AttentionList {...attention} onOpen={openIncident} showAssignee={false} />
                </Grid>
                <Grid size={{xs: 12, md: 5}}>
                    <SlaCard sla={period.sla} current={current} rangeLabel={rangeLabel} compareTo={compareTo} onShowBreached={() => showAttention('sla_breached')} />
                </Grid>
            </Grid>

            <SectionLabel detail={rangeLabel}>My speed</SectionLabel>
            <TileRow tiles={[
                speedTile('Time to acknowledge', VisibilityIcon, period.timings.acknowledge, compareTo),
                speedTile('Time to resolve', DoneAllIcon, period.timings.resolve, compareTo),
                keptInformedTile(communication, () => showAttention('silent')),
            ]} />

            <Grid container spacing={2}>
                <Grid size={{xs: 12, md: 7, lg: 8}}>
                    <TrendChart period={period} rangeLabel={rangeLabel} />
                </Grid>
                <Grid size={{xs: 12, md: 5, lg: 4}}>
                    <CategoryChart items={period.by_category} rangeLabel={rangeLabel} onSelect={(category) => mine({category: [category]})} />
                </Grid>
            </Grid>

            <SectionLabel>Team</SectionLabel>
            <WorkloadCard engineers={data.workload} rangeLabel={rangeLabel} highlightUserId={userId} />
        </Stack>
    );
}

// ---------- Employee: my tickets ----------

function EmployeeDashboard({data, ctx}) {
    const {current, period} = data;
    const {openIncidents, openIncident} = ctx;
    const response = period.timings.acknowledge;

    return (
        <Stack spacing={2}>
            <SectionLabel>Your incidents right now</SectionLabel>
            <TileRow tiles={[
                {
                    label: 'Open tickets', icon: ConfirmationNumberIcon, value: current.active,
                    caption: `${current.by_status.Open} waiting · ${current.by_status['In Progress']} being worked on`,
                    onClick: () => openIncidents({status: ACTIVE_STATUSES}),
                },
                {
                    label: 'Needs your confirmation', icon: TaskAltIcon, tone: 'success', value: current.awaiting_reporter, muted: !current.awaiting_reporter,
                    caption: 'resolved: close it, or reopen if not fixed',
                    onClick: () => openIncidents({status: ['Resolved']}),
                },
                {
                    label: 'On hold', icon: BlockIcon, tone: 'error', value: current.blocked, muted: !current.blocked,
                    caption: 'blocked, reason shown on the ticket',
                    onClick: () => openIncidents({status: ['Blocked']}),
                },
                {
                    label: 'Typical response time', icon: ForumIcon, value: formatDuration(response.median_hours),
                    caption: response.count ? `from report to an engineer picking it up, across ${plural(response.count, 'ticket')}` : 'no responses yet',
                },
            ]} />
            <SectionLabel>Your tickets</SectionLabel>
            <MyTickets tickets={data.my_tickets} onOpen={openIncident} />
        </Stack>
    );
}

function LoadingSkeleton() {
    return (
        <Grid container spacing={2}>
            {[...Array(6)].map((_, i) => <Grid key={i} size={{xs: 6, sm: 4, lg: 2}}><Skeleton variant="rounded" height={120} /></Grid>)}
            <Grid size={{xs: 12, md: 7}}><Skeleton variant="rounded" height={360} /></Grid>
            <Grid size={{xs: 12, md: 5}}><Skeleton variant="rounded" height={360} /></Grid>
        </Grid>
    );
}

{/**
 * per-persona dashboard. live counts ("right now") ignore the date range; speed, SLA, trends,
 * categories and locations use it. tiles, alerts and chart bars link to the matching incidents
 */}
function DashboardPage() {
    const {role} = usePermissions();
    const {user, profile} = useAuth();
    const {navigate} = useNavigation();
    const isAdmin = role === ROLES.FACILITY_ADMIN;
    const isEmployee = role === ROLES.EMPLOYEE;

    // employees only see live state + all-time response speed, so they get no range picker
    const [range, setRange] = useState(isEmployee ? {preset: 'all'} : DEFAULT_RANGE);
    // null until the admin picks: then they start on their home facility (if they have one), else all facilities
    const [pickedFacilityIds, setPickedFacilityIds] = useState(null);
    const homeFacilityId = profile?.facility_id;
    const facilityIds = useMemo(() => pickedFacilityIds ?? (homeFacilityId ? [homeFacilityId] : []), [pickedFacilityIds, homeFacilityId]);
    const [buildingId, setBuildingId] = useState(null);
    const [attentionFilter, setAttentionFilter] = useState(null);
    const attentionRef = useRef(null);
    const facilityOptions = useOptions(facilitiesService, (f) => f.name, {enabled: isAdmin});
    const allBuildingOptions = useOptions(buildingsService, (b) => b.name, {enabled: isAdmin});
    const buildingOptions = useMemo(() => (facilityIds.length
        ? allBuildingOptions.filter((o) => facilityIds.includes(o.row.facility_id))
        : allBuildingOptions), [allBuildingOptions, facilityIds]);
    const {data, error, loading, loadedAt, refresh} = useDashboard({
        range, facilityIds: isAdmin ? facilityIds : [], buildingId,
        // wait for the profile so an admin's first load is already on their home facility
        enabled: !isAdmin || profile !== undefined,
    });

    const changeFacilities = (ids) => {
        setPickedFacilityIds(ids);
        const stillVisible = allBuildingOptions.some((o) => o.value === buildingId && (!ids.length || ids.includes(o.row.facility_id)));
        if (!stillVisible) setBuildingId(null);
    };
    // more than one campus on screen: label locations and engineers with their facility
    const facilityNames = toLabelMap(facilityOptions);
    const showFacility = isAdmin && facilityOptions.length > 1 && facilityIds.length !== 1;

    const rangeLabel = describeRange(range);
    const ctx = {
        rangeLabel,
        compareTo: describePreviousRange(range),
        showFacility,
        facilityNames,
        // drill-down keeps the dashboard's facility/building filters
        openIncidents: (filters) => navigate('incidents', {filters: {
            ...(isAdmin && facilityIds.length && {facility_id: facilityIds}),
            ...(buildingId != null && {building_id: buildingId}),
            ...filters,
        }}),
        openIncident: (incidentId) => navigate('incidents', {incidentId}),
        showAttention: (kind) => {
            setAttentionFilter(kind);
            attentionRef.current?.scrollIntoView({behavior: 'smooth', block: 'start'});
        },
        // the attention list loads its own pages, with the same scope as the dashboard and reloading with it
        attention: {
            filter: attentionFilter,
            onFilterChange: setAttentionFilter,
            scope: {facility_id: isAdmin ? facilityIds : [], building_id: buildingId ?? undefined},
            refreshKey: loadedAt?.getTime(),
        },
    };

    const updated = loadedAt ? ` · updated ${loadedAt.toLocaleTimeString(undefined, {timeStyle: 'short'})}` : '';
    const titles = {
        [ROLES.FACILITY_ADMIN]: ['Operations dashboard', `${describeFacilities(facilityIds, facilityNames)}${updated}`],
        [ROLES.ENGINEER]: ['My dashboard', `Your assigned tickets and team capacity${profile?.facility_name ? ` at ${profile.facility_name}` : ''}${updated}`],
        [ROLES.EMPLOYEE]: [`Hi ${user?.sub ?? 'there'}`, `Here's where your reported issues stand${updated}`],
    };
    const [title, subtitle] = titles[role] ?? titles[ROLES.EMPLOYEE];

    return (
        <Stack spacing={2}>
            <DashboardToolbar
                title={title}
                subtitle={subtitle}
                range={isEmployee ? null : range}
                onRangeChange={setRange}
                facilityOptions={isAdmin && facilityOptions.length > 1 ? facilityOptions : null}
                facilityIds={facilityIds}
                onFacilityChange={changeFacilities}
                buildingOptions={isAdmin ? buildingOptions : null}
                buildingId={buildingId}
                onBuildingChange={setBuildingId}
                onRefresh={refresh}
                loading={loading}
                actions={isEmployee && (
                    <Button variant="contained" startIcon={<AddIcon />} onClick={() => navigate('incidents', {create: true})}>
                        Report an issue
                    </Button>
                )}
            />

            {error && (
                <Alert severity="error" action={<Button color="inherit" size="small" onClick={refresh}>Retry</Button>}>
                    Couldn't load the dashboard: {error}
                </Alert>
            )}

            {/* keeps the old numbers visible (dimmed) while a new range loads, so the layout doesn't jump */}
            <Box sx={{position: 'relative'}}>
                {loading && data && <LinearProgress sx={{position: 'absolute', top: -10, left: 0, right: 0, height: 2}} />}
                {!data && !error && <LoadingSkeleton />}
                {data && (
                    <Box sx={{opacity: loading ? 0.6 : 1, transition: 'opacity 150ms'}}>
                        {data.scope === 'all' && <AdminDashboard data={data} ctx={ctx} attentionRef={attentionRef} />}
                        {data.scope === 'assigned' && <EngineerDashboard data={data} ctx={ctx} attentionRef={attentionRef} userId={user?.uid} />}
                        {data.scope === 'reported' && <EmployeeDashboard data={data} ctx={ctx} />}
                    </Box>
                )}
            </Box>
        </Stack>
    );
}

export default DashboardPage;
