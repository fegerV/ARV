import jsPDF from 'jspdf';

export const downloadQRAsPNG = (canvasElement: HTMLCanvasElement, filename: string) => {
  const url = canvasElement.toDataURL('image/png');
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
};

export const downloadQRAsSVG = async (value: string, filename: string) => {
  const QRCode = (await import('qrcode')).default;
  
  const svg = await QRCode.toString(value, {
    type: 'svg',
    width: 300,
    margin: 2,
  });
  
  const blob = new Blob([svg], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
};

export const downloadQRAsPDF = async (canvasElement: HTMLCanvasElement, filename: string, arUrl: string) => {
  const pdf = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  // Title
  pdf.setFontSize(16);
  pdf.text('Vertex AR QR Code', 105, 20, { align: 'center' });

  // QR Code
  const imgData = canvasElement.toDataURL('image/png');
  const qrSize = 80; // mm
  const x = (210 - qrSize) / 2; // Center on A4
  const y = 40;
  pdf.addImage(imgData, 'PNG', x, y, qrSize, qrSize);

  // URL
  pdf.setFontSize(10);
  pdf.text(arUrl, 105, y + qrSize + 10, { align: 'center' });

  // Instructions
  pdf.setFontSize(12);
  pdf.text('Scan with mobile device to view AR content', 105, y + qrSize + 20, { align: 'center' });

  pdf.save(filename);
};
