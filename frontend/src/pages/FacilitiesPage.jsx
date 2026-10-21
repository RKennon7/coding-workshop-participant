import { useMemo, useState } from 'react';
import { Box, Tab, Tabs } from '@mui/material';
import ResourceView from '../components/common/ResourceView.jsx';
import { PERMISSIONS } from '../auth/permissions.js';
import { toLabelMap, useOptions } from '../hooks/useResource.js';
import { buildingsService, facilitiesService, floorsService, seatsService } from '../services/index.js';

// facilities > buildings > floors > seats all share the same manage permission
const FACILITY_PERMISSIONS = {
    create: PERMISSIONS.FACILITIES_MANAGE,
    update: PERMISSIONS.FACILITIES_MANAGE,
    delete: PERMISSIONS.FACILITIES_MANAGE,
};

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
            columns={columns} fields={fields} permissions={FACILITY_PERMISSIONS} />
    );
}

// buildings, floors and seats each belong to a parent, so they share this shape
function ChildView({title, singular, service, parent, labelField = 'name'}) {
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
            getRowLabel={(row) => row[labelField]} />
    );
}

const SUB_TABS = [
    {label: 'Facilities', render: () => <FacilitiesView />},
    {
        label: 'Buildings',
        render: () => <ChildView title="Buildings" singular="Building" service={buildingsService}
            parent={{field: 'facility_id', label: 'Facility', service: facilitiesService}} />,
    },
    {
        label: 'Floors',
        render: () => <ChildView title="Floors" singular="Floor" service={floorsService}
            parent={{field: 'building_id', label: 'Building', service: buildingsService}} />,
    },
    {
        label: 'Seats',
        render: () => <ChildView title="Seats" singular="Seat" service={seatsService} labelField="code"
            parent={{field: 'floor_id', label: 'Floor', service: floorsService}} />,
    },
];

function FacilitiesPage() {
    const [tab, setTab] = useState(0);
    return (
        <Box>
            <Tabs value={tab} onChange={(_, value) => setTab(value)} sx={{mb: 2}} variant="scrollable" allowScrollButtonsMobile>
                {SUB_TABS.map((t) => <Tab key={t.label} label={t.label} />)}
            </Tabs>
            {SUB_TABS[tab].render()}
        </Box>
    );
}

export default FacilitiesPage;
