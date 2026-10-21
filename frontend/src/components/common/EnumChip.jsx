import { Chip } from '@mui/material';

{/** small colored chip for enum values like status/priority. colors maps value -> MUI color */}
function EnumChip({value, colors}) {
    if (!value) {
        return null;
    }
    return <Chip label={value} color={colors[value] ?? 'default'} size="small" variant="outlined" />;
}

export default EnumChip;
