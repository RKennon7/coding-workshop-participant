/**
 * Light/dark mode. ColorModeProvider (mounted in main.jsx, around everything incl. the login screen) applies the
 * MUI theme from theme.js and remembers the choice in localStorage under 'colorMode'.
 * components/layout/ColorModeToggle.jsx calls toggleColorMode() from useColorMode().
 */
import {createContext, useContext, useMemo, useState, useEffect} from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import useMediaQuery from '@mui/material/useMediaQuery';
import { getTheme } from '../theme';

const ColorModeContext = createContext({ mode: 'light', toggleColorMode: () => {} });

/** @returns {{mode: 'light' | 'dark', toggleColorMode: () => void}} */
export const useColorMode = () => useContext(ColorModeContext);

/**
 * Provides the color mode and wraps children in MUI's ThemeProvider + CssBaseline.
 * Starts from the saved choice, else the OS preference (prefers-color-scheme). After that the
 * user's toggle wins: later OS changes are ignored.
 */
export function ColorModeProvider({children}) {
    // noSsr reads the real value on the first render so the initial mode below is correct
    const prefersDark = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true });
    const [mode, setMode] = useState(
        () => localStorage.getItem('colorMode') || (prefersDark ? 'dark' : 'light')
    );

    useEffect(() => {
        localStorage.setItem('colorMode', mode);
    }, [mode]);

    // memoised so consumers only re-render when the mode actually changes
    const value = useMemo(
        () => ({
            mode,
            toggleColorMode: () => setMode((m) => (m === 'light' ? 'dark' : 'light')),
        }),
        [mode]
    );

    // createTheme is fairly expensive, and a new theme object would restyle the whole tree
    const theme = useMemo(() => getTheme(mode), [mode]);

    return (
        <ColorModeContext.Provider value={value}>
          <ThemeProvider theme={theme}>
            <CssBaseline />
            {children}
          </ThemeProvider>
        </ColorModeContext.Provider>
    );

}