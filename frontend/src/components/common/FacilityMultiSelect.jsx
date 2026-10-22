// multi-select dropdown of facilities (campuses) with a checkbox per option.
// only shown to Facility Admins: the dashboard toolbar and the incident filters render it for admins only,
// since employees and engineers are limited to their own campus by the backend anyway.
import { Checkbox, ListItemText, MenuItem, TextField } from '@mui/material';

{/**
 * Admin-only facility picker. An empty selection means "all facilities".
 *  - options: [{value, label}] from useOptions(facilitiesService, ...)
 *  - value / onChange: array of facility ids
 *  - sx: extra styles merged over the default min width
 * selecting every facility is shown as "All facilities" too, but the value stays the full list of ids
 */}
function FacilityMultiSelect({options, value = [], onChange, sx}) {
    const labels = Object.fromEntries(options.map((option) => [option.value, option.label]));
    return (
        <TextField
            select
            label="Facility"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            sx={{minWidth: 180, ...sx}}
            slotProps={{
                // keep the label above the input and render a value even when nothing is selected ("All facilities")
                inputLabel: {shrink: true},
                select: {
                    multiple: true,
                    displayEmpty: true,
                    renderValue: (selected) => {
                        if (selected.length === 0 || selected.length === options.length) return 'All facilities';
                        if (selected.length === 1) return labels[selected[0]] ?? '1 facility';
                        return `${selected.length} facilities`;
                    },
                },
            }}
        >
            {options.map((option) => (
                <MenuItem key={option.value} value={option.value} dense>
                    <Checkbox size="small" checked={value.includes(option.value)} sx={{py: 0}} />
                    <ListItemText primary={option.label} />
                </MenuItem>
            ))}
        </TextField>
    );
}

export default FacilityMultiSelect;
