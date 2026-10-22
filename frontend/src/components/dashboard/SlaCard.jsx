import { Box, LinearProgress, Link, Stack, Typography } from '@mui/material';
import { Gauge, gaugeClasses } from '@mui/x-charts/Gauge';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import ReportOutlinedIcon from '@mui/icons-material/ReportOutlined';
import DashboardCard from './DashboardCard.jsx';
import Delta from './Delta.jsx';
import EnumChip from '../common/EnumChip.jsx';
import { successTone } from './dashboardMeta.js';
import { PRIORITY_COLORS } from '../../constants/enums.js';
import { formatDuration } from '../../utils/format.js';

const TONE_ICON = {success: CheckCircleIcon, warning: WarningAmberIcon, error: ReportOutlinedIcon};
const TONE_LABEL = {success: 'On target', warning: 'Slipping', error: 'Off target'};

{/** share of tickets resolved within their priority's target time, overall + per priority */}
function SlaCard({sla, current, rangeLabel, compareTo, onShowBreached}) {
    const tone = successTone(sla.met_pct);
    const ToneIcon = TONE_ICON[tone];

    return (
        <DashboardCard title="Resolution SLA" subtitle={`Tickets resolved within target, ${rangeLabel}`}>
            <Stack direction={{xs: 'column', sm: 'row'}} spacing={2} sx={{alignItems: {xs: 'flex-start', sm: 'center'}}}>
                <Box sx={{width: 132, height: 132, flexShrink: 0, alignSelf: 'center'}}>
                    <Gauge
                        value={sla.met_pct ?? 0}
                        startAngle={-110}
                        endAngle={110}
                        innerRadius="78%"
                        cornerRadius="50%"
                        text={sla.met_pct == null ? '–' : `${Math.round(sla.met_pct)}%`}
                        sx={(theme) => ({
                            [`& .${gaugeClasses.valueText} text`]: {fontSize: 28, fontWeight: 700, fill: theme.palette.text.primary},
                            [`& .${gaugeClasses.valueArc}`]: {fill: tone === 'default' ? theme.palette.text.disabled : theme.palette[tone].main},
                            [`& .${gaugeClasses.referenceArc}`]: {fill: theme.palette.action.disabledBackground},
                        })}
                    />
                </Box>
                <Box sx={{minWidth: 0}}>
                    {ToneIcon && (
                        <Stack direction="row" spacing={0.75} sx={{alignItems: 'center', color: `${tone}.main`}}>
                            <ToneIcon fontSize="small" />
                            <Typography variant="subtitle2" sx={{fontWeight: 600}}>{TONE_LABEL[tone]}</Typography>
                        </Stack>
                    )}
                    <Typography variant="body2" sx={{mt: 0.5}}>
                        {sla.resolved
                            ? <><strong>{sla.met}</strong> of <strong>{sla.resolved}</strong> resolved tickets met their target</>
                            : 'No tickets resolved in this period yet'}
                    </Typography>
                    <Delta current={sla.met_pct} previous={sla.previous_met_pct} format={(v) => `${v.toFixed(0)} pts`} compareTo={compareTo} />
                    {current.sla_breached > 0 && (
                        <Link component="button" variant="body2" color="error" onClick={onShowBreached} sx={{display: 'block', mt: 1, fontWeight: 600, textAlign: 'left'}}>
                            {current.sla_breached} open ticket{current.sla_breached === 1 ? ' is' : 's are'} past target now
                        </Link>
                    )}
                </Box>
            </Stack>

            <Stack spacing={1.25} sx={{mt: 2}}>
                {sla.by_priority.map((row) => {
                    const pct = row.resolved ? (100 * row.met) / row.resolved : null;
                    const rowTone = successTone(pct);
                    return (
                        <Box key={row.priority} sx={{display: 'grid', gridTemplateColumns: '84px 1fr auto', alignItems: 'center', columnGap: 1.5}}>
                            <Box><EnumChip value={row.priority} colors={PRIORITY_COLORS} /></Box>
                            <Box sx={{minWidth: 0}}>
                                <LinearProgress
                                    variant="determinate"
                                    value={pct ?? 0}
                                    color={rowTone === 'default' ? 'inherit' : rowTone}
                                    sx={{height: 6, borderRadius: 3, bgcolor: 'action.hover', color: 'text.disabled'}}
                                    aria-label={`${row.priority} SLA met`}
                                />
                                <Typography variant="caption" color="text.secondary">
                                    target {formatDuration(row.target_hours)}
                                </Typography>
                            </Box>
                            <Typography variant="body2" sx={{fontWeight: 600, textAlign: 'right', minWidth: 52}}>
                                {row.resolved ? `${row.met}/${row.resolved}` : '–'}
                            </Typography>
                        </Box>
                    );
                })}
            </Stack>
        </DashboardCard>
    );
}

export default SlaCard;
