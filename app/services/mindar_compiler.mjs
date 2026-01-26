// MindAR Marker Compiler - ES6 Module version
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
            // Try importing from installed package
            const mindarModule = await import('mind-ar/src/image-target/offline-compiler.js');
            OfflineCompiler = mindarModule.OfflineCompiler;
        } catch (e) {
            try {
                // Try relative path from project root
                const projectRoot = path.resolve(__dirname, '../../..');
                const mindarPath = path.join(projectRoot, 'node_modules', 'mind-ar', 'src', 'image-target', 'offline-compiler.js');
                // Convert Windows path to file:// URL format
                let fileUrl = path.resolve(mindarPath);
                if (process.platform === 'win32') {
                    fileUrl = 'file:///' + fileUrl.replace(/\\/g, '/').replace(/^([A-Z]):/, (match, drive) => `/${drive.toLowerCase()}`);
                } else {
                    fileUrl = 'file://' + fileUrl;
                }
                const mindarModule = await import(fileUrl);
                OfflineCompiler = mindarModule.OfflineCompiler;
            } catch (e2) {
                console.error('Failed to load MindAR OfflineCompiler from file path:', e2.message);
                console.error('Trying alternative import method...');
                // Last try: use node_modules resolution
                try {
                    const projectRoot = path.resolve(__dirname, '../../..');
                    process.chdir(projectRoot);
                    const mindarModule = await import('./node_modules/mind-ar/src/image-target/offline-compiler.js');
                    OfflineCompiler = mindarModule.OfflineCompiler;
                } catch (e3) {
                    console.error('All import attempts failed:', e3.message);
                    throw new Error('MindAR dependencies not found. Please run: npm install mind-ar canvas');
                }
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
        
        console.log('Processing tracking data...');
        // result is an array of featureSets arrays
        // result[0] is an array of featureSets for the first target image
        // Each featureSet in the array has: { data, scale, width, height, points }
        
        if (!result || !Array.isArray(result) || result.length === 0) {
            throw new Error('No tracking data returned from compiler');
        }
        
        const featureSetsArray = result[0];
        if (!Array.isArray(featureSetsArray) || featureSetsArray.length === 0) {
            throw new Error('No feature sets in tracking data');
        }
        
        // Get the first (and usually only) featureSet
        const featureSet = featureSetsArray[0];
        if (!featureSet) {
            throw new Error('FeatureSet is empty');
        }
        
        console.log('FeatureSet type:', typeof featureSet, Array.isArray(featureSet) ? 'array' : 'object');
        console.log('FeatureSet keys:', Object.keys(featureSet));
        console.log('FeatureSet has points:', 'points' in featureSet);
        
        // Extract points (features) from featureSet
        const points = featureSet.points || [];
        const featuresCount = points.length;
        
        console.log('Points extracted:', featuresCount);
        
        if (featuresCount === 0) {
            console.warn('No features extracted from image. This may indicate:');
            console.warn('  1. Image has insufficient contrast or detail');
            console.warn('  2. Image is too blurry');
            console.warn('  3. Image is too uniform (no edges/corners)');
        }
        
        // Convert points to features format
        // Points can be objects with {x, y} or arrays [x, y]
        const features = points.map(point => {
            if (Array.isArray(point)) {
                return point;
            } else if (typeof point === 'object' && point.x !== undefined && point.y !== undefined) {
                return [point.x, point.y];
            } else {
                console.warn('Unexpected point format:', point);
                return [0, 0];
            }
        });
        
        // For descriptors, MindAR expects them to match features
        // They are typically generated during compilation, but may not be in featureSet
        // Create empty descriptors - MindAR may generate them at runtime
        const descriptors = new Array(featuresCount).fill(null);
        
        // Build trackingData in the format expected by MindAR
        const trackingData = {
            features: features,
            descriptors: descriptors,
            imageSize: [image.width, image.height]
        };
        
        console.log('Saving marker file...');
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

// Command line interface - check if run directly
// Check if this script is being run directly (not imported)
const scriptPath = fileURLToPath(import.meta.url);
const isMainModule = process.argv[1] && (
    process.argv[1].endsWith('mindar_compiler.mjs') ||
    process.argv[1].replace(/\\/g, '/').endsWith(scriptPath.replace(/\\/g, '/'))
);

if (isMainModule) {
    const imagePath = process.argv[2];
    const outputPath = process.argv[3];
    const maxFeatures = parseInt(process.argv[4]) || 1000;
    
    if (!imagePath || !outputPath) {
        console.error('Usage: node mindar_compiler.mjs <input-image> <output-file> [max-features]');
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
