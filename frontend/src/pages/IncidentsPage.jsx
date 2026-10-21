import { useMemo } from 'react';
import ResourceView from '../components/common/ResourceView.jsx';
import EnumChip from '../components/common/EnumChip.jsx';
import IncidentNotes from '../components/incidents/IncidentNotes.jsx';
import IncidentHistory from '../components/incidents/IncidentHistory.jsx';
import { PERMISSIONS } from '../auth/permissions.js';
import { canEditIncidentField, statusChoices } from '../auth/incidentRules.js';
import { useAuth } from '../context/AuthContext.jsx';
import { usePermissions } from '../hooks/usePermissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { buildingsService, engineersService, floorsService, incidentsService, seatsService } from '../services/index.js';
import {
    INCIDENT_CATEGORIES, INCIDENT_PRIORITIES, INCIDENT_STATUSES, PRIORITY_COLORS, STATUS_COLORS, toOptions,
} from '../constants/enums.js';
import { formatDateTime } from '../utils/format.js';

const P = PERMISSIONS;

// the select needs the current assignee among its options even when the user can't list engineers
function withCurrentAssignee(options, incident) {
    const assignee = incident?.assignee;
    if (!assignee || options.some((option) => option.value === assignee.id)) {
        return options;
    }
    return [...options, {value: assignee.id, label: assignee.username}];
}

function IncidentsPage() {
    const {can} = usePermissions();
    const {user} = useAuth();

    const buildingOptions = useOptions(buildingsService, (b) => b.name);
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
            {field: 'id', headerName: 'ID', width: 70},
            {field: 'title', headerName: 'Title', flex: 2, minWidth: 200},
            {
                field: 'status', headerName: 'Status', width: 130,
                type: 'singleSelect', valueOptions: INCIDENT_STATUSES,
                renderCell: ({value}) => <EnumChip value={value} colors={STATUS_COLORS} />,
            },
            {
                field: 'priority', headerName: 'Priority', width: 110,
                type: 'singleSelect', valueOptions: INCIDENT_PRIORITIES,
                renderCell: ({value}) => <EnumChip value={value} colors={PRIORITY_COLORS} />,
            },
            {field: 'category', headerName: 'Category', width: 150, type: 'singleSelect', valueOptions: INCIDENT_CATEGORIES},
            {field: 'reporter_id', headerName: 'Reporter', width: 140, valueGetter: (value, row) => row.reporter?.username ?? value},
            {
                field: 'building_id', headerName: 'Building', width: 150,
                valueGetter: (value, row) => row.building?.name ?? buildings[value] ?? value,
            },
            {
                field: 'assignee_id', headerName: 'Assignee', width: 150,
                valueGetter: (value, row) => row.assignee?.username ?? engineers[value] ?? (value ? `User #${value}` : 'Unassigned'),
            },
            {field: 'is_escalated', headerName: 'Escalated', width: 100, type: 'boolean'},
            {
                field: 'created_at', headerName: 'Created', width: 180,
                type: 'dateTime', valueGetter: (value) => (value ? new Date(value) : null),
                valueFormatter: (value) => formatDateTime(value),
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
                name: 'assignee_id', label: 'Assignee', type: 'select', hideOnCreate: true, editableBy: rule('assignee_id'),
                options: (values, incident) => withCurrentAssignee(engineerOptions, incident),
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
            permissions={{create: P.INCIDENTS_CREATE, update: P.INCIDENTS_UPDATE, delete: P.INCIDENTS_DELETE}}
            getRowLabel={(row) => `#${row.id} ${row.title}`}
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
