import { Box, Typography, Grid, Card, CardContent, Paper } from '@mui/material';
import {
  Visibility as ViewsIcon,
  People as SessionsIcon,
  ViewInAr as ContentIcon,
  Storage as StorageIcon,
  Business as CompaniesIcon,
  Folder as ProjectsIcon,
  AttachMoney as RevenueIcon,
  CheckCircle as UptimeIcon,
} from '@mui/icons-material';

const statsCards = [
  { title: 'Total AR Views', value: '45,892', change: '+12.5%', icon: <ViewsIcon fontSize="large" />, color: '#1976d2' },
  { title: 'Unique Sessions', value: '38,234', change: '+8.2%', icon: <SessionsIcon fontSize="large" />, color: '#2e7d32' },
  { title: 'Active Content', value: '280', change: '+15', icon: <ContentIcon fontSize="large" />, color: '#9c27b0' },
  { title: 'Storage Usage', value: '125GB', change: '10%', icon: <StorageIcon fontSize="large" />, color: '#ed6c02' },
  { title: 'Active Companies', value: '15', change: '+2', icon: <CompaniesIcon fontSize="large" />, color: '#0288d1' },
  { title: 'Active Projects', value: '100', change: '+12', icon: <ProjectsIcon fontSize="large" />, color: '#7b1fa2' },
  { title: 'Revenue', value: '$4,200', change: '+15%', icon: <RevenueIcon fontSize="large" />, color: '#2e7d32' },
  { title: 'Uptime', value: '99.92%', change: '✅', icon: <UptimeIcon fontSize="large" />, color: '#4caf50' },
];

export default function Dashboard() {
  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {statsCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card elevation={2}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box>
                    <Typography color="textSecondary" variant="caption" gutterBottom>
                      {stat.title}
                    </Typography>
                    <Typography variant="h5" sx={{ fontWeight: 700, my: 1 }}>
                      {stat.value}
                    </Typography>
                    <Typography variant="body2" color="success.main">
                      {stat.change}
                    </Typography>
                  </Box>
                  <Box sx={{ color: stat.color }}>
                    {stat.icon}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Box sx={{ mt: 4 }}>
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Recent Activity
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Activity feed будет здесь...
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
}
