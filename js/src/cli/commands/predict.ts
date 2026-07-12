// sage predict
import { FailurePredictor } from '../../ml/index.js';

export async function predictCmd(cmdParts: string[]): Promise<void> {
  if (cmdParts.length === 0) {
    console.error('Usage: sage predict <command>');
    process.exit(1);
  }

  const command = cmdParts.join(' ');
  const predictor = new FailurePredictor();
  const prediction = predictor.predict(command);

  console.log('Failure Prediction');
  console.log('─'.repeat(40));
  console.log(`Command: ${command}`);
  console.log();
  
  // Visual risk indicator
  const riskPercent = Math.round(prediction.risk * 100);
  const riskBar = '█'.repeat(Math.round(riskPercent / 5)) + '░'.repeat(20 - Math.round(riskPercent / 5));
  
  let riskLevel: string;
  let riskColor: string;
  if (riskPercent < 20) {
    riskLevel = 'LOW';
    riskColor = '\x1b[32m'; // Green
  } else if (riskPercent < 50) {
    riskLevel = 'MEDIUM';
    riskColor = '\x1b[33m'; // Yellow
  } else if (riskPercent < 80) {
    riskLevel = 'HIGH';
    riskColor = '\x1b[31m'; // Red
  } else {
    riskLevel = 'VERY HIGH';
    riskColor = '\x1b[91m'; // Bright red
  }

  console.log(`Risk: ${riskColor}${riskPercent}% ${riskLevel}\x1b[0m`);
  console.log(`      [${riskBar}]`);
  console.log();
  console.log(`Confidence: ${Math.round(prediction.confidence * 100)}%`);
  console.log(`Reason: ${prediction.reason}`);

  if (prediction.risk > 0.5) {
    console.log();
    console.log('⚠️  High risk detected. Consider:');
    if (command.includes('rm -rf') || command.includes('del /')) {
      console.log('  - Double-check the path before running');
      console.log('  - Consider using trash/recycle instead of permanent delete');
    }
    if (command.includes('--force') || command.includes('-f')) {
      console.log('  - Remove --force flag if not necessary');
    }
    if (command.includes('sudo') || command.includes('admin')) {
      console.log('  - Verify you need elevated privileges');
    }
  }
}
