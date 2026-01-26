// Use dynamic import for ES6 modules
import { createCanvas, loadImage } from 'canvas';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

async function generateMarker(imagePath, outputPath, maxFeatures = 1000) {
    try {
        // Dynamically import OfflineCompiler (ES6 module)
        let OfflineCompiler;
        try {
            // Try different possible paths
            const mindarModule = await import('mind-ar/src/image-target/offline-compiler.js');
            OfflineCompiler = mindarModule.OfflineCompiler;
        } catch (e) {
            try {
                // Try relative path from project root
                const projectRoot = path.resolve(__dirname, '../../..');
                const mindarPath = path.join(projectRoot, 'node_modules', 'mind-ar', 'src', 'image-target', 'offline-compiler.js');
                const mindarModule = await import('file:///' + mindarPath.replace(/\\/g, '/'));
                OfflineCompiler = mindarModule.OfflineCompiler;
            } catch (e2) {
                console.error('Failed to load MindAR OfflineCompiler:', e2.message);
                throw new Error('MindAR dependencies not found. Please run: npm install mind-ar canvas');
            }
        }
        
        console.log('Loading image:', imagePath);
        const image = await loadImage(imagePath);
        
        console.log('Initializing compiler...');
        const compiler = new OfflineCompiler();
        
        console.log('Compiling target...');
        const processCanvas = createCanvas(image.width, image.height);
        const ctx = processCanvas.getContext('2d');
        ctx.drawImage(image, 0, 0, image.width, image.height);
        
        const imageData = ctx.getImageData(0, 0, image.width, image.height);
        const greyImageData = new Uint8Array(image.width * image.height);
        
        for (let i = 0; i < greyImageData.length; i++) {
            const offset = i * 4;
            greyImageData[i] = Math.floor(
                (imageData.data[offset] + imageData.data[offset + 1] + imageData.data[offset + 2]) / 3
            );
        }
        
        const targetImage = {
            data: greyImageData,
            width: image.width,
            height: image.height
        };
        
        const result = await compiler.compileTrack({
            targetImages: [targetImage],
            basePercent: 0,
            progressCallback: (percent) => {
                console.log(`Progress: ${percent.toFixed(1)}%`);
            }
        });
        
        console.log('Saving marker file...');
        const trackingData = result[0] || {};
        const featuresCount = trackingData.features ? trackingData.features.length : 0;
        
        const markerData = {
            version: 2,
            type: 'image',
            width: image.width,
            height: image.height,
            trackingData: trackingData
        };
        
        fs.writeFileSync(outputPath, JSON.stringify(markerData));
        console.log('Marker saved to:', outputPath);
        console.log('Features extracted:', featuresCount);
        
        return {
            success: true,
            width: image.width,
            height: image.height,
            features: featuresCount
        };
        
    } catch (error) {
        console.error('Error generating marker:', error);
        return {
            success: false,
            error: error.message
        };
    }
}

// Command line interface
// Check if this is the main module (ES6 way)
if (import.meta.url === `file://${process.argv[1]}`.replace(/\\/g, '/')) {
    const imagePath = process.argv[2];
    const outputPath = process.argv[3];
    const maxFeatures = parseInt(process.argv[4]) || 1000;
    
    if (!imagePath || !outputPath) {
        console.error('Usage: node mindar_compiler.js <input-image> <output-file> [max-features]');
        process.exit(1);
    }
    
    generateMarker(imagePath, outputPath, maxFeatures)
        .then(result => {
            if (result.success) {
                console.log('Marker generation completed successfully');
                console.log(JSON.stringify(result));
                process.exit(0);
            } else {
                console.error('Marker generation failed:', result.error);
                process.exit(1);
            }
        })
        .catch(error => {
            console.error('Unexpected error:', error);
            process.exit(1);
        });
}

export { generateMarker };
