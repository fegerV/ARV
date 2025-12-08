import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Tabs,
  Tab,
  Paper,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  Avatar,
} from '@mui/material';
import { ArrowBack as BackIcon, Edit as EditIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { PageHeader, PageContent } from '@/components';
import { useToast } from '@/store/useToast';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index } = props;
  return value === index ? <Box sx={{ py: 3 }}>{children}</Box> : null;
}

export default function ARContentDetails() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [tabValue, setTabValue] = useState(0);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const content = {
    id: parseInt(id || '1'),
    title: 'Santa with Gifts',
    company: 'OOO Art Studio',
    project: 'New Year 2025',
    status: 'active',
    totalViews: 8924,
  };

  const handleDeleteContent = () => {
    showToast('AR content deleted', 'success');
    navigate('/ar-content');
    setDeleteConfirm(false);
  };

  return (
    <PageContent>
      <PageHeader
        title={content.title}
        subtitle={`${content.company} / ${content.project}`}
        actions={
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button startIcon={<BackIcon />} onClick={() => navigate('/ar-content')} variant="outlined">
              Back
            </Button>
            <Button startIcon={<EditIcon />} variant="contained">
              Edit
            </Button>
            <Button startIcon={<DeleteIcon />} onClick={() => setDeleteConfirm(true)} color="error">
              Delete
            </Button>
          </Box>
        }
      />

      <Paper>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="Overview" />
          <Tab label="Videos" />
          <Tab label="Analytics" />
          <Tab label="Activity" />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6">Content Info</Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Status</Typography>
                    <Chip label={content.status.toUpperCase()} color="success" size="small" />
                  </Box>
                  <Box>
                    <Typography variant="body2" color="textSecondary">Total Views</Typography>
                    <Typography variant="h6">{content.totalViews}</Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Alert severity="info">Videos will be managed here</Alert>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Alert severity="info">Analytics data will be displayed here</Alert>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        <Alert severity="info">Activity log will be shown here</Alert>
      </TabPanel>

      <Dialog open={deleteConfirm} onClose={() => setDeleteConfirm(false)}>
        <DialogTitle>Delete AR Content?</DialogTitle>
        <DialogContent>
          <Typography>This action cannot be undone.</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteConfirm(false)}>Cancel</Button>
          <Button onClick={handleDeleteContent} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </PageContent>
  );
}
