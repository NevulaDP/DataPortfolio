import React, { useState, useEffect } from 'react';
import Split from 'react-split';
import Editor from '@monaco-editor/react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  TextField,
  IconButton,
  Divider,
  CircularProgress
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { executor } from '../utils/executor';

// We'll define these types again or move to a shared file later
interface ProjectDefinition {
    title: string;
    description: string;
    tasks: string[];
    schema: any[];
    insights: string[];
    data_issues: string[];
}

interface WorkspaceProps {
    project: {
        definition: ProjectDefinition;
        data: any[];
    };
}

interface ChatMessage {
    sender: 'user' | 'agent';
    text: string;
}

const Workspace: React.FC<WorkspaceProps> = ({ project }) => {
    const [activeTab, setActiveTab] = useState(0); // 0: Python, 1: SQL
    const [pythonCode, setPythonCode] = useState(`# Access your data using the variable 'df'\nimport pandas as pd\n\nprint(df.head())`);
    const [sqlCode, setSqlCode] = useState(`SELECT * FROM dataset LIMIT 5`);
    const [output, setOutput] = useState<string>('');
    const [chatInput, setChatInput] = useState('');
    const [messages, setMessages] = useState<ChatMessage[]>([
        { sender: 'agent', text: `Hello! I'm your Senior Data Analyst mentor. I've prepared a project for you on **${project.definition.title}**. Check out the scenario on the left and let me know if you need help!` }
    ]);
    const [loadingChat, setLoadingChat] = useState(false);
    const [executing, setExecuting] = useState(false);
    const [initializing, setInitializing] = useState(true);

    useEffect(() => {
        const initExecutor = async () => {
            setOutput("Initializing execution engine...");
            await executor.loadData(project.data);
            setOutput("Execution engine ready. Data loaded.");
            setInitializing(false);
        };
        initExecutor();
    }, [project.data]);

    const handleRunCode = async () => {
        setExecuting(true);
        setOutput("Running...");
        try {
            let res = "";
            if (activeTab === 0) {
                res = await executor.runPython(pythonCode);
            } else {
                res = await executor.runSQL(sqlCode);
            }
            setOutput(res);
        } catch (e) {
            setOutput("Error during execution.");
        } finally {
            setExecuting(false);
        }
    };

    const handleSendMessage = async () => {
        if (!chatInput.trim()) return;

        const newMessage: ChatMessage = { sender: 'user', text: chatInput };
        setMessages(prev => [...prev, newMessage]);
        setChatInput('');
        setLoadingChat(true);

        try {
            const context = `Project: ${project.definition.title}. Scenario: ${project.definition.description}`;
            const res = await axios.post('http://localhost:8000/api/chat', {
                message: newMessage.text,
                context: context
            });
            setMessages(prev => [...prev, { sender: 'agent', text: res.data.response }]);
        } catch (err) {
            setMessages(prev => [...prev, { sender: 'agent', text: "Error connecting to mentor." }]);
        } finally {
            setLoadingChat(false);
        }
    };

    return (
        <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex' }}>
            <Split
                sizes={[25, 50, 25]}
                minSize={100}
                expandToMin={false}
                gutterSize={10}
                gutterAlign="center"
                snapOffset={30}
                dragInterval={1}
                direction="horizontal"
                cursor="col-resize"
                style={{ display: 'flex', width: '100%' }}
            >
                {/* Panel 1: Scenario & Tasks */}
                <Paper sx={{ overflow: 'auto', p: 2, height: '100%' }}>
                    <Typography variant="h6">{project.definition.title}</Typography>
                    <Typography variant="body2" paragraph>{project.definition.description}</Typography>

                    <Typography variant="subtitle1" sx={{ mt: 2, fontWeight: 'bold' }}>Tasks</Typography>
                    <List dense>
                        {project.definition.tasks.map((task, i) => (
                            <ListItem key={i}>
                                <ListItemText primary={`${i+1}. ${task}`} />
                            </ListItem>
                        ))}
                    </List>

                    <Typography variant="subtitle1" sx={{ mt: 2, fontWeight: 'bold' }}>Data Schema</Typography>
                    <List dense>
                         {project.definition.schema.map((col: any, i: number) => (
                            <ListItem key={i}>
                                <ListItemText primary={col.name} secondary={col.type} />
                            </ListItem>
                         ))}
                    </List>
                </Paper>

                {/* Panel 2: Code Editor & Output */}
                <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <Paper square>
                        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
                            <Tab label="Python" />
                            <Tab label="SQL" />
                            <Box sx={{ flexGrow: 1 }} />
                            <IconButton color="primary" onClick={handleRunCode} disabled={executing || initializing}>
                                {executing ? <CircularProgress size={24} /> : <PlayArrowIcon />}
                            </IconButton>
                        </Tabs>
                    </Paper>
                    <Box sx={{ flexGrow: 1 }}>
                        <Editor
                            height="100%"
                            defaultLanguage={activeTab === 0 ? "python" : "sql"}
                            language={activeTab === 0 ? "python" : "sql"}
                            value={activeTab === 0 ? pythonCode : sqlCode}
                            onChange={(val) => activeTab === 0 ? setPythonCode(val || '') : setSqlCode(val || '')}
                            theme="vs-light"
                            options={{ minimap: { enabled: false } }}
                        />
                    </Box>
                    <Divider />
                    <Paper sx={{ height: '30%', p: 1, overflow: 'auto', bgcolor: '#f5f5f5' }}>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                            {output}
                        </Typography>
                    </Paper>
                </Box>

                {/* Panel 3: Chatbot */}
                <Paper sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white' }}>
                        <Typography variant="subtitle1">Senior Mentor</Typography>
                    </Box>
                    <Box sx={{ flexGrow: 1, overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {messages.map((msg, i) => (
                            <Paper
                                key={i}
                                sx={{
                                    p: 1.5,
                                    maxWidth: '90%',
                                    alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
                                    bgcolor: msg.sender === 'user' ? 'primary.light' : 'grey.100',
                                    color: msg.sender === 'user' ? 'white' : 'text.primary'
                                }}
                            >
                                <ReactMarkdown>{msg.text}</ReactMarkdown>
                            </Paper>
                        ))}
                         {loadingChat && <Typography variant="caption" sx={{ ml: 2 }}>Typing...</Typography>}
                    </Box>
                    <Box sx={{ p: 1, display: 'flex' }}>
                        <TextField
                            fullWidth
                            size="small"
                            placeholder="Ask for help..."
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                        />
                        <IconButton onClick={handleSendMessage} disabled={loadingChat}>
                            <SendIcon />
                        </IconButton>
                    </Box>
                </Paper>
            </Split>
        </Box>
    );
};

export default Workspace;
