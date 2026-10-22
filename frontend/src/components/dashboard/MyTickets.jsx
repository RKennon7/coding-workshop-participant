import { Box, Card, CardActionArea, Chip, Grid, Stack, Step, StepLabel, Stepper, Typography } from '@mui/material';
import EnumChip from '../common/EnumChip.jsx';
import { EmptyState } from './DashboardCard.jsx';
import { FLAG_META, formatLocation } from './dashboardMeta.js';
import { PRIORITY_COLORS } from '../../constants/enums.js';
import { formatAgo } from '../../utils/format.js';

const STEPS = ['Reported', 'In progress', 'Resolved', 'Closed'];
const STEP_INDEX = {'Open': 0, 'In Progress': 1, 'Blocked': 1, 'Resolved': 2, 'Closed': 3};

{/** where the ticket is in the workflow. Blocked shows as a red "In progress" step with the reason */}
function TicketProgress({ticket}) {
    const active = STEP_INDEX[ticket.status];
    const blocked = ticket.status === 'Blocked';
    return (
        <Stepper activeStep={active} alternativeLabel sx={{my: 1.5, '& .MuiStepLabel-label': {mt: 0.5, fontSize: 12}}}>
            {STEPS.map((label, index) => {
                const isBlockedStep = blocked && index === active;
                return (
                    <Step key={label} completed={index < active || (index === active && ticket.status === 'Resolved')}>
                        <StepLabel error={isBlockedStep}>{isBlockedStep ? 'Blocked' : label}</StepLabel>
                    </Step>
                );
            })}
        </Stepper>
    );
}

function TicketCard({ticket, onOpen}) {
    const blockedFlag = ticket.flags.find((f) => f.kind === 'blocked');
    const otherFlags = ticket.flags.filter((f) => f.kind !== 'blocked');
    return (
        <Card sx={{height: '100%'}}>
            <CardActionArea onClick={() => onOpen(ticket.id)} sx={{height: '100%', p: 2, display: 'flex', flexDirection: 'column', alignItems: 'stretch', justifyContent: 'flex-start'}}>
                <Stack direction="row" spacing={1} sx={{alignItems: 'flex-start'}}>
                    <Typography variant="subtitle2" sx={{flex: 1, fontWeight: 600}}>#{ticket.id} {ticket.title}</Typography>
                    <EnumChip value={ticket.priority} colors={PRIORITY_COLORS} />
                </Stack>
                <Typography variant="caption" color="text.secondary">
                    {formatLocation(ticket.location)} · {ticket.assignee ? `Engineer: ${ticket.assignee.username}` : 'Waiting for an engineer'}
                </Typography>

                <TicketProgress ticket={ticket} />
                {blockedFlag?.detail && (
                    <Typography variant="body2" color="error.main" sx={{mb: 1}}>On hold: {blockedFlag.detail}</Typography>
                )}

                {/* the latest thing ACME told the employee about this ticket */}
                <Box sx={{bgcolor: 'action.hover', borderRadius: 2, px: 1.5, py: 1}}>
                    <Typography variant="caption" color="text.secondary">Latest update · {formatAgo(ticket.last_update_at)}</Typography>
                    <Typography variant="body2" sx={{display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>
                        {ticket.last_update ?? (ticket.status === 'Open' ? 'Your ticket has been received.' : `Status changed to ${ticket.status}.`)}
                    </Typography>
                </Box>

                {otherFlags.length > 0 && (
                    <Stack direction="row" useFlexGap sx={{flexWrap: 'wrap', gap: 0.75, mt: 1.5}}>
                        {otherFlags.map((flag) => {
                            const {label, color, icon: Icon} = FLAG_META[flag.kind];
                            return <Chip key={flag.kind} size="small" color={color} variant={flag.kind === 'awaiting_reporter' ? 'filled' : 'outlined'} icon={<Icon />} label={label} />;
                        })}
                    </Stack>
                )}
            </CardActionArea>
        </Card>
    );
}

{/** an employee's open + resolved tickets as cards, those waiting on them first */}
function MyTickets({tickets, onOpen}) {
    if (tickets.length === 0) {
        return <Card><EmptyState>You have no open tickets. Report an issue whenever something needs fixing.</EmptyState></Card>;
    }
    return (
        <Grid container spacing={2}>
            {tickets.map((ticket) => (
                <Grid key={ticket.id} size={{xs: 12, md: 6, xl: 4}}>
                    <TicketCard ticket={ticket} onOpen={onOpen} />
                </Grid>
            ))}
        </Grid>
    );
}

export default MyTickets;
