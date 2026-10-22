// light/dark theme switch in the AppHeader, available to every logged-in role.
// the mode itself lives in ColorModeContext, which starts from the OS preference and remembers the
// choice in localStorage ('colorMode').
import { IconButton } from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import { useColorMode } from '../../context/ColorModeContext';

/**
 * Icon button that flips between light and dark mode. Takes no props.
 * the icon shows the mode currently active (moon in dark mode, sun in light mode), not the one you'd switch to.
 */
function ColorModeToggle() {
    const {mode, toggleColorMode} = useColorMode();
    return (
        <IconButton color="inherit" onClick={toggleColorMode} aria-label='Toggle light/dark theme'>
          {mode === 'dark' ? <DarkModeIcon /> : <LightModeIcon />}
        </IconButton>
    );
}
export default ColorModeToggle;