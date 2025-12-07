import React, { useState } from 'react';
import axios from 'axios';
import {
  Container,
  Typography,
  TextField,
  Button,
  Box,
  Paper,
  CircularProgress
} from '@mui/material';

// Types
export interface ProjectDefinition {
  title: string;
  description: string;
  tasks: string[];
  schema: any[];
  insights: string[];
  data_issues: string[];
}

interface ProjectData {
  definition: ProjectDefinition;
  data: any[];
}

interface LandingProps {
  onProjectGenerated: (data: ProjectData) => void;
}

const Landing: React.FC<LandingProps> = ({ onProjectGenerated }) => {
  const [sector, setSector] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!sector) return;
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('http://localhost:8000/api/generate_project', { sector });
      onProjectGenerated(response.data);
    } catch (err) {
      setError('Failed to generate project. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 6, textAlign: 'center' }}>
        <Typography variant="h3" component="h1" gutterBottom>
          Junior Data Analyst Portfolio Builder
        </Typography>
        <Typography variant="h6" color="textSecondary" paragraph>
          Enter a sector (e.g., Retail, Healthcare, Finance) to generate a realistic project with synthetic data.
        </Typography>

        <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center' }}>
          <TextField
            label="Sector"
            variant="outlined"
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            disabled={loading}
            sx={{ width: '300px' }}
          />
          <Button
            variant="contained"
            size="large"
            onClick={handleGenerate}
            disabled={loading || !sector}
          >
            {loading ? <CircularProgress size={24} /> : 'Start Project'}
          </Button>
        </Box>
        {error && (
          <Typography color="error" sx={{ mt: 2 }}>
            {error}
          </Typography>
        )}
      </Paper>
    </Container>
  );
};

export default Landing;
