import { useState } from 'react';
import Landing from './components/Landing';
import Workspace from './components/Workspace';
import { createTheme, ThemeProvider, CssBaseline, AppBar, Toolbar, Typography } from '@mui/material';
import type { ProjectDefinition } from './components/Landing';

const theme = createTheme({
  palette: {
    mode: 'light',
  },
});

function App() {
  const [projectData, setProjectData] = useState<{ definition: ProjectDefinition; data: any[] } | null>(null);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Data Portfolio Builder
          </Typography>
        </Toolbar>
      </AppBar>

      {!projectData ? (
        <Landing onProjectGenerated={setProjectData} />
      ) : (
        <Workspace project={projectData} />
      )}
    </ThemeProvider>
  );
}

export default App;
