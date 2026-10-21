import { IconButton } from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import { useColorMode } from '../../context/ColorModeContext';

function ColorModeToggle() {
    const {mode, toggleColorMode} = useColorMode();
    return (
        <IconButton color="inherit" onClick={toggleColorMode} aria-label='Toggle light/dark theme'>
          {mode === 'dark' ? <DarkModeIcon /> : <LightModeIcon />}
        </IconButton>
    );
}
export default ColorModeToggle;