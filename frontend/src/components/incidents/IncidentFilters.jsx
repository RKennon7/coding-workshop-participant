// filter bar above the incidents grid (IncidentsPage passes it to ResourceView as `filters`).
// all roles see it, but the facility picker is admin-only and the assignee picker needs ENGINEERS_VIEW
// (engineers and admins). the backend still limits which incidents each role can see at all.
import { Button, Chip, MenuItem, Stack, TextField } from '@mui/material';
import FlagIcon from '@mui/icons-material/Flag';
import FilterAltOffIcon from '@mui/icons-material/FilterAltOff';
import { INCIDENT_CATEGORIES, INCIDENT_PRIORITIES, INCIDENT_STATUSES } from '../../constants/enums.js';
import { toListParams } from '../../utils/filters.js';
import FacilityMultiSelect from '../common/FacilityMultiSelect.jsx';

// sentinel option value in the assignee dropdown, turned into the API's ?unassigned=true instead of an assignee_id
const UNASSIGNED = 'unassigned';

// multi-select over plain string enums (status/priority/category). value is an array of strings
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

// single-select over [{value, label}] options with an "Any" entry. "Any" is reported as null (filter off)
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
 * Server-side filters for the incidents grid (the grid's own quick search still works on top).
 *  - filters: {status: [], priority: [], category: [], facility_id: [], building_id, floor_id, seat_id, assignee_id, unassigned, is_escalated}
 *    the parent turns this into query params with utils/filters.js toListParams (unset values are dropped)
 *  - onChange(filters): receives the whole new filter object, not just the changed keys
 *  - facilityOptions: admins only, omit to hide the facility picker. buildingOptions should already be narrowed to it
 *  - floorOptions / seatOptions: [{value, label}], only used to label the floor/seat chips
 *  - engineerOptions / showAssignee: the assignee picker (with an "Unassigned" choice), hidden when showAssignee is false
 *  - floor/seat have no dropdown, they come from dashboard links and show as removable chips
 */}
function IncidentFilters({filters, onChange, facilityOptions, buildingOptions, floorOptions, seatOptions, engineerOptions, showAssignee}) {
    const set = (changes) => onChange({...filters, ...changes});
    // chip label for a floor/seat id, falls back to #id if the options haven't loaded (or don't include it)
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
                    // unassigned and assignee_id are mutually exclusive, picking one clears the other
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
                // toggle chip: on sends ?is_escalated=true, off removes the filter (null), there's no "not escalated" filter
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
