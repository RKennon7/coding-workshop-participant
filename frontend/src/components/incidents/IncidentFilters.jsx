import { Button, Chip, MenuItem, Stack, TextField } from '@mui/material';
import FlagIcon from '@mui/icons-material/Flag';
import FilterAltOffIcon from '@mui/icons-material/FilterAltOff';
import { INCIDENT_CATEGORIES, INCIDENT_PRIORITIES, INCIDENT_STATUSES } from '../../constants/enums.js';
import { toListParams } from '../../utils/filters.js';
import FacilityMultiSelect from '../common/FacilityMultiSelect.jsx';

const UNASSIGNED = 'unassigned';

function MultiSelect({label, value = [], options, onChange}) {
    return (
        <TextField
            select
            label={label}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            sx={{minWidth: 150, flex: {xs: '1 1 140px', md: '0 0 auto'}}}
            slotProps={{
                select: {
                    multiple: true,
                    renderValue: (selected) => (selected.length <= 2 ? selected.join(', ') : `${selected.length} selected`),
                },
            }}
        >
            {options.map((option) => <MenuItem key={option} value={option}>{option}</MenuItem>)}
        </TextField>
    );
}

function SingleSelect({label, value, options, onChange}) {
    return (
        <TextField
            select
            label={label}
            value={value ?? ''}
            onChange={(event) => onChange(event.target.value === '' ? null : event.target.value)}
            sx={{minWidth: 150, flex: {xs: '1 1 140px', md: '0 0 auto'}}}
        >
            <MenuItem value=""><em>Any</em></MenuItem>
            {options.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
        </TextField>
    );
}

{/**
 * server-side filters for the incidents grid (the grid's own quick search still works on top)
 *  - filters: {status: [], priority: [], category: [], facility_id: [], building_id, floor_id, seat_id, assignee_id, unassigned, is_escalated}
 *  - facilityOptions: admins only, omit to hide the facility picker. buildingOptions should already be narrowed to it
 *  - floor/seat have no dropdown, they come from dashboard links and show as removable chips
 */}
function IncidentFilters({filters, onChange, facilityOptions, buildingOptions, floorOptions, seatOptions, engineerOptions, showAssignee}) {
    const set = (changes) => onChange({...filters, ...changes});
    const label = (options, id) => options.find((option) => option.value === id)?.label ?? `#${id}`;
    const hasFilters = Object.keys(toListParams(filters)).length > 0;

    return (
        <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 1.5, alignItems: 'center'}}>
            {facilityOptions && (
                <FacilityMultiSelect
                    options={facilityOptions}
                    value={filters.facility_id}
                    // a building outside the new facilities would leave the list empty
                    onChange={(facility_id) => set({facility_id, building_id: null, floor_id: null, seat_id: null})}
                    sx={{flex: {xs: '1 1 140px', md: '0 0 auto'}}}
                />
            )}
            <MultiSelect label="Status" value={filters.status} options={INCIDENT_STATUSES} onChange={(status) => set({status})} />
            <MultiSelect label="Priority" value={filters.priority} options={INCIDENT_PRIORITIES} onChange={(priority) => set({priority})} />
            <MultiSelect label="Category" value={filters.category} options={INCIDENT_CATEGORIES} onChange={(category) => set({category})} />
            <SingleSelect
                label="Building"
                value={filters.building_id}
                options={buildingOptions}
                // a floor/seat from another building would leave the list empty
                onChange={(building_id) => set({building_id, floor_id: null, seat_id: null})}
            />
            {showAssignee && (
                <SingleSelect
                    label="Assignee"
                    value={filters.unassigned ? UNASSIGNED : filters.assignee_id}
                    options={[{value: UNASSIGNED, label: 'Unassigned'}, ...engineerOptions]}
                    onChange={(value) => set(value === UNASSIGNED
                        ? {unassigned: true, assignee_id: null}
                        : {unassigned: null, assignee_id: value})}
                />
            )}
            <Chip
                icon={<FlagIcon />}
                label="Escalated only"
                color={filters.is_escalated ? 'warning' : 'default'}
                variant={filters.is_escalated ? 'filled' : 'outlined'}
                onClick={() => set({is_escalated: filters.is_escalated ? null : true})}
                aria-pressed={Boolean(filters.is_escalated)}
            />
            {filters.floor_id != null && (
                <Chip label={`Floor: ${label(floorOptions, filters.floor_id)}`} onDelete={() => set({floor_id: null, seat_id: null})} />
            )}
            {filters.seat_id != null && (
                <Chip label={`Seat: ${label(seatOptions, filters.seat_id)}`} onDelete={() => set({seat_id: null})} />
            )}
            {hasFilters && (
                <Button size="small" startIcon={<FilterAltOffIcon />} onClick={() => onChange({})}>
                    Clear filters
                </Button>
            )}
        </Stack>
    );
}

export default IncidentFilters;
