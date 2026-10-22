import { useMemo, useState } from 'react';
import { Alert, Box, Button, Snackbar, Stack, Tab, Tabs } from '@mui/material';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import ResourceView from '../components/common/ResourceView.jsx';
import FacilitySetupDialog from '../components/facilities/FacilitySetupDialog.jsx';
import { PERMISSIONS } from '../auth/permissions.js';
import { usePermissions } from '../hooks/usePermissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { buildingsService, facilitiesService, fetchDeleteImpact, floorsService, seatsService } from '../services/index.js';

// facilities > buildings > floors > seats all share the same manage permission
const FACILITY_PERMISSIONS = {
    create: PERMISSIONS.FACILITIES_MANAGE,
    update: PERMISSIONS.FACILITIES_MANAGE,
    delete: PERMISSIONS.FACILITIES_MANAGE,
};

const plural = (count, word) => `${count} ${word}${count === 1 ? '' : 's'}`;

// confirmation text from GET <path>/{id}/delete-impact: what goes with it, or why it can't be deleted
function deleteDetails(path, getLabel) {
    return async (row) => {
        const impact = await fetchDeleteImpact(path, row.id);
        const label = getLabel(row);
        if (impact.incidents) {
            return {
                blocked: true,
                message: (
                    <Alert severity="warning">
                        <strong>{label}</strong> has {plural(impact.incidents, 'incident')} recorded against it, so it can't be
                        deleted. Edit it and untick <strong>Active</strong> instead: it's hidden from new reports but its ticket history is kept.
                    </Alert>
                ),
            };
        }
        const contents = [
            impact.buildings && (path === '/facilities') && plural(impact.buildings, 'building'),
            impact.floors && path !== '/floors' && plural(impact.floors, 'floor'),
            impact.seats && plural(impact.seats, 'seat'),
        ].filter(Boolean);
        return {
            blocked: false,
            message: (
                <>
                    <strong>{label}</strong> will be permanently deleted
                    {contents.length > 0 && <>, along with everything in it: {contents.join(', ')}</>}.
                    {impact.users > 0 && (
                        <Alert severity="info" sx={{mt: 2}}>
                            {plural(impact.users, 'user')} assigned to this facility will be left without one until you
                            reassign them on the Users page. They can still log in but won't see any locations.
                        </Alert>
                    )}
                </>
            ),
        };
    };
}

const activeColumn = {field: 'is_active', headerName: 'Active', width: 90, type: 'boolean'};
const activeField = {name: 'is_active', label: 'Active', type: 'checkbox', defaultValue: true};

function FacilitiesView() {
    const columns = useMemo(() => [
        {field: 'id', headerName: 'ID', width: 70},
        {field: 'name', headerName: 'Name', flex: 1, minWidth: 180},
        {field: 'address', headerName: 'Address', flex: 2, minWidth: 220},
        activeColumn,
    ], []);
    const fields = useMemo(() => [
        {name: 'name', label: 'Name', required: true},
        {name: 'address', label: 'Address'},
        activeField,
    ], []);
    return (
        <ResourceView title="Facilities" singular="Facility" service={facilitiesService}
            columns={columns} fields={fields} permissions={FACILITY_PERMISSIONS}
            getDeleteDetails={deleteDetails('/facilities', (row) => row.name)} />
    );
}

// buildings, floors and seats each belong to a parent, so they share this shape
function ChildView({title, singular, service, path, parent, labelField = 'name'}) {
    const parentOptions = useOptions(parent.service, (row) => row[parent.labelField ?? 'name']);

    const columns = useMemo(() => {
        const parents = toLabelMap(parentOptions);
        return [
            {field: 'id', headerName: 'ID', width: 70},
            {field: labelField, headerName: labelField === 'code' ? 'Code' : 'Name', flex: 1, minWidth: 160},
            {
                field: parent.field, headerName: parent.label, flex: 1, minWidth: 160,
                valueGetter: (value) => parents[value] ?? value,
            },
            activeColumn,
        ];
    }, [parentOptions, labelField, parent.field, parent.label]);

    const fields = useMemo(() => [
        {name: labelField, label: labelField === 'code' ? 'Code' : 'Name', required: true},
        {name: parent.field, label: parent.label, type: 'select', options: parentOptions, required: true},
        activeField,
    ], [parentOptions, labelField, parent.field, parent.label]);

    return (
        <ResourceView title={title} singular={singular} service={service}
            columns={columns} fields={fields} permissions={FACILITY_PERMISSIONS}
            getRowLabel={(row) => row[labelField]}
            getDeleteDetails={deleteDetails(path, (row) => row[labelField])} />
    );
}

const SUB_TABS = [
    {label: 'Facilities', render: () => <FacilitiesView />},
    {
        label: 'Buildings',
        render: () => <ChildView title="Buildings" singular="Building" service={buildingsService} path="/buildings"
            parent={{field: 'facility_id', label: 'Facility', service: facilitiesService}} />,
    },
    {
        label: 'Floors',
        render: () => <ChildView title="Floors" singular="Floor" service={floorsService} path="/floors"
            parent={{field: 'building_id', label: 'Building', service: buildingsService}} />,
    },
    {
        label: 'Seats',
        render: () => <ChildView title="Seats" singular="Seat" service={seatsService} path="/seats" labelField="code"
            parent={{field: 'floor_id', label: 'Floor', service: floorsService}} />,
    },
];

function FacilitiesPage() {
    const {can} = usePermissions();
    const [tab, setTab] = useState(0);
    const [setupOpen, setSetupOpen] = useState(false);
    const [toast, setToast] = useState(null);
    // bumped after a bulk setup so the grids reload with the new rows
    const [version, setVersion] = useState(0);
    const facilityOptions = useOptions(facilitiesService, (f) => f.name, {enabled: setupOpen});

    const handleCreated = ({facility, buildings, floors, seats}) => {
        setSetupOpen(false);
        setVersion((v) => v + 1);
        setToast(`${facility.name}: added ${buildings} building${buildings === 1 ? '' : 's'}, ${floors} floors and ${seats} seats`);
    };

    return (
        <Box>
            <Stack direction="row" sx={{alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 2, flexWrap: 'wrap'}}>
                <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" allowScrollButtonsMobile sx={{minWidth: 0}}>
                    {SUB_TABS.map((t) => <Tab key={t.label} label={t.label} />)}
                </Tabs>
                {can(PERMISSIONS.FACILITIES_MANAGE) && (
                    <Button variant="outlined" startIcon={<AddBusinessIcon />} onClick={() => setSetupOpen(true)}>
                        Set up facility
                    </Button>
                )}
            </Stack>
            <Box key={version}>{SUB_TABS[tab].render()}</Box>

            {setupOpen && (
                <FacilitySetupDialog open onClose={() => setSetupOpen(false)} onCreated={handleCreated} facilityOptions={facilityOptions} />
            )}
            <Snackbar open={Boolean(toast)} autoHideDuration={5000} onClose={() => setToast(null)} anchorOrigin={{vertical: 'bottom', horizontal: 'center'}}>
                <Alert severity="success" variant="filled" onClose={() => setToast(null)}>{toast}</Alert>
            </Snackbar>
        </Box>
    );
}

export default FacilitiesPage;
