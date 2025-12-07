// components/media/VideoListVirtualized.tsx
import React from 'react';
import { FixedSizeList, ListChildComponentProps } from 'react-window';
import { Box } from '@mui/material';
import { VideoPreview } from './VideoPreview';
import { Video } from './VideoPreview';

interface VideoListVirtualizedProps {
  videos: Video[];
  height?: number;
  rowHeight?: number;
  onVideoClick?: (video: Video) => void;
}

export const VideoListVirtualized: React.FC<VideoListVirtualizedProps> = ({
  videos,
  height = 320,
  rowHeight = 90,
  onVideoClick,
}) => {
  const Row = ({ index, style }: ListChildComponentProps) => {
    const video = videos[index];
    return (
      <Box style={style} px={1}>
        <VideoPreview
          video={video}
          size="small"
          onClick={() => onVideoClick?.(video)}
        />
      </Box>
    );
  };

  return (
    <FixedSizeList
      height={height}
      width="100%"
      itemCount={videos.length}
      itemSize={rowHeight}
    >
      {Row}
    </FixedSizeList>
  );
};