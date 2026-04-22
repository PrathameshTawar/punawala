import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import VideoCall from './VideoCall';

test('renders recording button', () => {
  render(<VideoCall onAudioReady={() => {}} isRecording={false} />);
  const button = screen.getByText(/LIVE/i);
  expect(button).toBeInTheDocument();
});