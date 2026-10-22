// the dashboard's header row: page title plus the controls that scope every card below it
// (time range, facility and building filters, refresh). renders no /analytics data itself; the chosen range and
// filters become the query of GET /analytics/dashboard in hooks/useDashboard.js. every role sees it, but
// employees get no range picker and only Facility Admins get the facility/building filters
import { useState } from 'react';
import { Box, IconButton, MenuItem, Stack, TextField, ToggleButton, ToggleButtonGroup, Tooltip, Typography } from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import FacilityMultiSelect from '../common/FacilityMultiSelect.jsx';

// values match PRESET_DAYS in hooks/useDashboard.js ('all' and 'custom' are handled there separately)
const PRESETS = [
    {value: '7d', label: '7d'},
    {value: '30d', label: '30d'},
    {value: '90d', label: '90d'},
    {value: 'all', label: 'All'},
    {value: 'custom', label: 'Custom'},
];

// YYYY-MM-DD in local time, the format <input type="date"> uses
const toDateInput = (date) => {
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 10);
};

{/**
 * page title + controls: time range (presets or custom dates), facility + building filters (admins), refresh
 *  - range: omit (null) to hide the time range controls, as for employees
 *  - range / onRangeChange: see hooks/useDashboard.js for the shape
 *  - facilityOptions: [{value, label}], omit to hide the facility filter (admins only, and only with more than one facility)
 *  - buildingOptions: [{value, label}], omit to hide the building filter
 *  - actions: extra elements placed before the filters (e.g. the employee's "Report an issue" button)
 */}
function DashboardToolbar({
    title, subtitle, range, onRangeChange, facilityOptions, facilityIds, onFacilityChange,
    buildingOptions, buildingId, onBuildingChange, onRefresh, loading, actions,
}) {
    // custom dates are edited here and only applied once both are valid
    const [draft, setDraft] = useState(() => (range?.preset === 'custom'
        ? {from: range.from, to: range.to}
        // default draft: the last 30 days including today
        : {from: toDateInput(new Date(Date.now() - 29 * 86_400_000)), to: toDateInput(new Date())}));
    const today = toDateInput(new Date());
    const draftValid = Boolean(draft.from && draft.to && draft.from <= draft.to);

    // an invalid pair (start after end) stays in the draft with an error and is not sent
    const changeDraft = (changes) => {
        const next = {...draft, ...changes};
        setDraft(next);
        if (next.from && next.to && next.from <= next.to) {
            onRangeChange({preset: 'custom', ...next});
        }
    };

    const changePreset = (_, preset) => {
        if (!preset) return;  // clicking the selected button again would unselect it
        onRangeChange(preset === 'custom' ? {preset, ...draft} : {preset});
    };

    return (
        <Stack direction={{xs: 'column', lg: 'row'}} spacing={2} sx={{justifyContent: 'space-between', alignItems: {xs: 'stretch', lg: 'center'}}}>
            <Box>
                <Typography variant="h5" component="h2">{title}</Typography>
                {subtitle && <Typography variant="body2" color="text.secondary">{subtitle}</Typography>}
            </Box>
            <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 1, alignItems: 'center'}}>
                {actions}
                {facilityOptions && <FacilityMultiSelect options={facilityOptions} value={facilityIds} onChange={onFacilityChange} />}
                {buildingOptions && (
                    <TextField
                        select
                        label="Building"
                        value={buildingId ?? ''}
                        onChange={(event) => onBuildingChange(event.target.value === '' ? null : event.target.value)}
                        sx={{minWidth: 160}}
                        slotProps={{select: {displayEmpty: true}, inputLabel: {shrink: true}}}
                    >
                        <MenuItem value="">All buildings</MenuItem>
                        {buildingOptions.map((option) => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
                    </TextField>
                )}
                {range && (
                    <ToggleButtonGroup size="small" exclusive value={range.preset} onChange={changePreset} aria-label="Time range">
                        {PRESETS.map(({value, label}) => <ToggleButton key={value} value={value} sx={{px: 1.5}}>{label}</ToggleButton>)}
                    </ToggleButtonGroup>
                )}
                {range?.preset === 'custom' && (
                    <>
                        <TextField
                            type="date"
                            label="From"
                            value={draft.from}
                            onChange={(event) => changeDraft({from: event.target.value})}
                            error={!draftValid}
                            slotProps={{inputLabel: {shrink: true}, htmlInput: {max: draft.to || today}}}
                        />
                        <TextField
                            type="date"
                            label="To"
                            value={draft.to}
                            onChange={(event) => changeDraft({to: event.target.value})}
                            error={!draftValid}
                            helperText={draftValid ? undefined : 'Pick a start date on or before the end date'}
                            slotProps={{inputLabel: {shrink: true}, htmlInput: {min: draft.from, max: today}}}
                        />
                    </>
                )}
                <Tooltip title="Refresh">
                    <span>{/* lets the tooltip still get hover events while the button is disabled (MUI requirement) */}
                        <IconButton onClick={onRefresh} disabled={loading} aria-label="Refresh dashboard">
                            <RefreshIcon />
                        </IconButton>
                    </span>
                </Tooltip>
            </Stack>
        </Stack>
    );
}

export default DashboardToolbar;
