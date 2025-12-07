// src/components/(analytics)/TopContentTable.tsx
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
} from '@mui/material';
import { TopContentItem } from '@/services/analyticsService';

interface TopContentTableProps {
  data: TopContentItem[];
}

export const TopContentTable: React.FC<TopContentTableProps> = ({ data }) => {
  if (!data.length) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="200px">
        <Typography>No data available</Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Title</TableCell>
            <TableCell align="right">Views</TableCell>
            <TableCell align="right">Avg Duration (sec)</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((item) => (
            <TableRow key={item.id} sx={{ '&:last-child td, &:last-child th': { border: 0 } }}>
              <TableCell component="th" scope="row">
                {item.title}
              </TableCell>
              <TableCell align="right">{item.views}</TableCell>
              <TableCell align="right">{item.avg_duration}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};