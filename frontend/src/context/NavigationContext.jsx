import { createContext, useContext } from 'react';

/**
 * Lets any page switch the main tab and hand the next page some params, e.g. the dashboard
 * opening the Incidents tab already filtered: navigate('incidents', {filters: {status: ['Blocked']}})
 * MainLayout provides the value; the active page receives the params as a `params` prop.
 */

export const NavigationContext = createContext(null);

export function useNavigation() {
    const context = useContext(NavigationContext);
    if (context === null) {
        throw new Error('useNavigation must be used within MainLayout');
    }
    return context;
}
