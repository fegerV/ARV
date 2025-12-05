import { Box, Typography, Button, Paper, Table, TableHead, TableBody, TableRow, TableCell, Chip, IconButton } from '@mui/material';
import { Add as AddIcon, Visibility as ViewIcon } from '@mui/icons-material';
import { useNavigate, useParams } from 'react-router-dom';

export default function ARContentList() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId: string }>();

  // Mock data
  const contentList = [
    {
      id: 456,
      title: 'Постер #1 - Санта с подарками',
      markerStatus: 'ready',
      videosCount: 5,
      views: 3245,
      uniqueId: 'abc123',
    },
  ];

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">AR Content</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate(`/projects/${projectId}/content/new`)}
        >
          New AR Content
        </Button>
      </Box>

      <Paper sx={{ p: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Marker Status</TableCell>
              <TableCell>Videos</TableCell>
              <TableCell>Views</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {contentList.map((content) => (
              <TableRow key={content.id}>
                <TableCell>{content.title}</TableCell>
                <TableCell>
                  <Chip 
                    label={content.markerStatus === 'ready' ? '✅ Ready' : '⏳ Processing'}
                    color={content.markerStatus === 'ready' ? 'success' : 'default'}
                    size="small"
                  />
                </TableCell>
                <TableCell>{content.videosCount}</TableCell>
                <TableCell>{content.views.toLocaleString()}</TableCell>
                <TableCell>
                  <IconButton 
                    size="small" 
                    onClick={() => navigate(`/ar-content/${content.id}`)}
                    title="View Details"
                  >
                    <ViewIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>
    </Box>
  );
}
