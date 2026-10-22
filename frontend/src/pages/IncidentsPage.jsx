/**
 * The Incidents tab: the paged ticket grid, filter bar and create/edit form, built on the generic
 * ResourceView (components/common/ResourceView.jsx) over /incidents.
 * Everyone sees this tab; the backend decides which tickets come back (admins: all, engineers: assigned
 * to or reported by them, employees: reported by them; see _visible_to in backend/v1/app/routers/incidents.py). Field-level edit rules come from auth/incidentRules.js.
 */
import { useMemo, useState } from 'react';
import { useMediaQuery } from '@mui/material';
import ResourceView from '../components/common/ResourceView.jsx';
import EnumChip from '../components/common/EnumChip.jsx';
import IncidentNotes from '../components/incidents/IncidentNotes.jsx';
import IncidentHistory from '../components/incidents/IncidentHistory.jsx';
import IncidentFilters from '../components/incidents/IncidentFilters.jsx';
import { PERMISSIONS, ROLES } from '../auth/permissions.js';
import { canEditIncidentField, statusChoices } from '../auth/incidentRules.js';
import { useAuth } from '../context/AuthContext.jsx';
import { usePermissions } from '../hooks/usePermissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { buildingsService, engineersService, facilitiesService, floorsService, incidentsService, seatsService } from '../services/index.js';
import {
    INCIDENT_CATEGORIES, INCIDENT_PRIORITIES, INCIDENT_STATUSES, PRIORITY_COLORS, STATUS_COLORS, toOptions,
} from '../constants/enums.js';
import { formatDate, formatDateTime } from '../utils/format.js';
import { toListParams } from '../utils/filters.js';

const P = PERMISSIONS;

// hidden by default on tablets/phones (users can turn them back on from the grid's column menu)
const COMPACT_HIDDEN_COLUMNS = {category: false, reporter_id: false, building_id: false, is_escalated: false, created_at: false};

// the select needs the current assignee among its options even when the user can't list engineers
function withCurrentAssignee(options, incident) {
    const assignee = incident?.assignee;
    if (!assignee || options.some((option) => option.value === assignee.id)) {
        return options;
    }
    return [...options, {value: assignee.id, label: assignee.username}];
}

{/**
 * Incidents page. params (from the dashboard, via MainLayout / NavigationContext):
 *  - filters: initial filter values, see IncidentFilters
 *  - incidentId: open that incident's form straight away
 *  - create: open the "new incident" form straight away
 */}
function IncidentsPage({params}) {
    const {can} = usePermissions();
    const {user, profile} = useAuth();
    const isAdmin = user?.role === ROLES.FACILITY_ADMIN;
    // admins with a home facility start filtered to it (they can clear it to see every facility)
    const [filters, setFilters] = useState(() => params?.filters
        ?? (isAdmin && profile?.facility_id ? {facility_id: [profile.facility_id]} : {}));
    const compact = useMediaQuery((theme) => theme.breakpoints.down('md'), {noSsr: true});
    // filter values -> query params for GET /incidents (unset filters are dropped)
    const listParams = useMemo(() => toListParams(filters), [filters]);

    // only admins filter by facility: everyone else is limited to their own campus by the backend
    const facilityOptions = useOptions(facilitiesService, (f) => f.name, {enabled: isAdmin});
    const buildingOptions = useOptions(buildingsService, (b) => b.name);
    // the filter bar only offers buildings in the picked facilities
    const filterBuildingOptions = useMemo(() => (filters.facility_id?.length
        ? buildingOptions.filter((o) => filters.facility_id.includes(o.row.facility_id))
        : buildingOptions), [buildingOptions, filters.facility_id]);
    const floorOptions = useOptions(floorsService, (f) => f.name);
    const seatOptions = useOptions(seatsService, (s) => s.code);
    // assignee_id is a user id, so engineer options use the profile's user_id
    const engineerOptions = useOptions(engineersService, (e) => (e.is_available ? e.display_name : `${e.display_name} (unavailable)`), {
        getValue: (e) => e.user_id,
        enabled: can(P.ENGINEERS_VIEW),
    });

    const columns = useMemo(() => {
        const buildings = toLabelMap(buildingOptions);
        const engineers = toLabelMap(engineerOptions);
        return [
            // flex columns share the leftover width, minWidths keep the whole grid under ~1200px so it fits a laptop
            {field: 'id', headerName: 'ID', width: 64},
            {field: 'title', headerName: 'Title', flex: 2, minWidth: 170},
            {
                field: 'status', headerName: 'Status', width: 118,
                type: 'singleSelect', valueOptions: INCIDENT_STATUSES,
                renderCell: ({value}) => <EnumChip value={value} colors={STATUS_COLORS} />,
            },
            {
                field: 'priority', headerName: 'Priority', width: 100,
                type: 'singleSelect', valueOptions: INCIDENT_PRIORITIES,
                renderCell: ({value}) => <EnumChip value={value} colors={PRIORITY_COLORS} />,
            },
            {field: 'category', headerName: 'Category', flex: 1, minWidth: 120, type: 'singleSelect', valueOptions: INCIDENT_CATEGORIES},
            // rows embed reporter/assignee/building objects; the label maps are a fallback for ids only
            {field: 'reporter_id', headerName: 'Reporter', flex: 1, minWidth: 105, valueGetter: (value, row) => row.reporter?.username ?? value},
            {
                field: 'building_id', headerName: 'Building', flex: 1, minWidth: 110,
                valueGetter: (value, row) => row.building?.name ?? buildings[value] ?? value,
            },
            {
                field: 'assignee_id', headerName: 'Assignee', flex: 1, minWidth: 110,
                valueGetter: (value, row) => row.assignee?.username ?? engineers[value] ?? (value ? `User #${value}` : 'Unassigned'),
            },
            {field: 'is_escalated', headerName: 'Escalated', width: 96, type: 'boolean'},
            {
                // date only to save space, the full timestamp is in the tooltip. still sorts/filters by exact time
                field: 'created_at', headerName: 'Created', width: 116,
                type: 'dateTime', valueGetter: (value) => (value ? new Date(value) : null),
                valueFormatter: (value) => formatDate(value),
                renderCell: ({value, formattedValue}) => <span title={formatDateTime(value)}>{formattedValue}</span>,
            },
        ];
    }, [buildingOptions, engineerOptions]);

    // what's editable depends on how the user relates to the ticket (admin / assigned engineer / reporter),
    // see auth/incidentRules.js -- same rules the backend enforces
    const fields = useMemo(() => {
        const rule = (name) => (row) => canEditIncidentField(row, user, name);
        return [
            {name: 'title', label: 'Title', required: true, editableBy: rule('title')},
            {name: 'description', label: 'Description', type: 'textarea', required: true, editableBy: rule('description')},
            {
                name: 'category', label: 'Category', type: 'select', options: toOptions(INCIDENT_CATEGORIES),
                required: true, editableBy: rule('category'),
            },
            {
                name: 'priority', label: 'Priority', type: 'select', options: toOptions(INCIDENT_PRIORITIES),
                defaultValue: 'Medium', required: true, editableBy: rule('priority'),
            },
            {
                // only offers moves this user may make from the ticket's saved status
                name: 'status', label: 'Status', type: 'select', required: true, hideOnCreate: true,
                options: (values, incident) => toOptions(statusChoices(incident, user)),
                editableBy: rule('status'),
            },
            {
                name: 'blocked_reason', label: 'Blocked Reason', type: 'textarea', hideOnCreate: true, required: true,
                hidden: (values) => values.status !== 'Blocked',
                editableBy: rule('blocked_reason'),
            },
            {name: 'building_id', label: 'Building', type: 'select', options: buildingOptions, required: true, editableBy: rule('building_id')},
            {
                name: 'floor_id', label: 'Floor', type: 'select', dependsOn: 'building_id', editableBy: rule('floor_id'),
                options: (values) => floorOptions.filter((o) => o.row.building_id === values.building_id),
            },
            {
                name: 'seat_id', label: 'Seat', type: 'select', dependsOn: 'floor_id', editableBy: rule('seat_id'),
                options: (values) => seatOptions.filter((o) => o.row.floor_id === values.floor_id),
            },
            {
                // only engineers who work at the incident's facility (the backend rejects anyone else)
                name: 'assignee_id', label: 'Assignee', type: 'select', hideOnCreate: true, editableBy: rule('assignee_id'),
                options: (values, incident) => {
                    const facilityId = buildingOptions.find((o) => o.value === values.building_id)?.row.facility_id;
                    return withCurrentAssignee(engineerOptions.filter((o) => o.row.facility_id === facilityId), incident);
                },
            },
            {
                name: 'is_escalated', label: 'Escalate this incident', type: 'checkbox', hideOnCreate: true,
                editableBy: rule('is_escalated'),
            },
            {
                name: 'escalation_reason', label: 'Escalation Reason', type: 'textarea', required: true,
                hidden: (values) => !values.is_escalated,
                editableBy: rule('escalation_reason'),
            },
        ];
    }, [buildingOptions, floorOptions, seatOptions, engineerOptions, user]);

    return (
        <ResourceView
            title="Incidents"
            singular="Incident"
            service={incidentsService}
            columns={columns}
            fields={fields}
            // update: the default for fields without editableBy (all incident fields have a row rule above)
            permissions={{create: P.INCIDENTS_CREATE, update: P.INCIDENTS_UPDATE, delete: P.INCIDENTS_DELETE}}
            getRowLabel={(row) => `#${row.id} ${row.title}`}
            listParams={listParams}
            gridInitialState={{columns: {columnVisibilityModel: compact ? COMPACT_HIDDEN_COLUMNS : {}}}}
            openRowId={params?.incidentId ?? null}
            initialCreate={Boolean(params?.create)}
            filters={(
                <IncidentFilters
                    filters={filters}
                    onChange={setFilters}
                    buildingOptions={filterBuildingOptions}
                    facilityOptions={isAdmin ? facilityOptions : null}
                    floorOptions={floorOptions}
                    seatOptions={seatOptions}
                    engineerOptions={engineerOptions}
                    showAssignee={can(P.ENGINEERS_VIEW)}
                />
            )}
            // shown under the edit form: status audit trail, then the notes thread (read-only once closed)
            renderFormExtras={(row) => (
                <>
                    <IncidentHistory incidentId={row.id} currentStatus={row.status} />
                    <IncidentNotes incidentId={row.id} closed={row.status === 'Closed'} />
                </>
            )}
        />
    );
}

export default IncidentsPage;
