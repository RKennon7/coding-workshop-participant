// small read-only chip for enum values (incident status, priority, ...), shown to every role.
// used in the incidents grid, the incident history timeline and the dashboard cards.
// the color maps live in constants/enums.js (e.g. STATUS_COLORS)
import { Chip } from '@mui/material';

{/**
 * Small colored chip for enum values like status/priority.
 *  - value: the enum string, also used as the label. renders nothing when empty
 *  - colors: {value: MUI color}, values missing from the map fall back to 'default'
 */}
function EnumChip({value, colors}) {
    if (!value) {
        return null;
    }
    return <Chip label={value} color={colors[value] ?? 'default'} size="small" variant="outlined" />;
}

export default EnumChip;
