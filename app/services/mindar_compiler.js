const { OfflineCompiler } = require('../../node_modules/mind-ar/src/image-target/offline-compiler.js');
const { createCanvas, loadImage } = require('canvas');
const fs = require('fs');
const path = require('path');

async function generateMarker(imagePath, outputPath, maxFeatures = 1000) {
    try {
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
        const markerData = {
            version: 2,
            type: 'image',
            width: image.width,
            height: image.height,
            trackingData: result[0] // result is an array with tracking data
        };
        
        fs.writeFileSync(outputPath, JSON.stringify(markerData));
        console.log('Marker saved to:', outputPath);
        
        return {
            success: true,
            width: image.width,
            height: image.height,
            features: result[0] ? Object.keys(result[0]).length : 0
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
if (require.main === module) {
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

module.exports = { generateMarker };
