import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import QuestList from './views/QuestList';
import QuestDetail from './views/QuestDetail';
import CreateQuest from './views/CreateQuest';
import UserProfile from './views/UserProfile';
import ProtectedRoute from './components/auth/ProtectedRoute';
import './index.css';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <QuestList /> },
      { path: 'quests/:questId', element: <QuestDetail /> },
      { 
        path: 'create-quest', 
        element: <ProtectedRoute><CreateQuest /></ProtectedRoute> 
      },
      { 
        path: 'profile', 
        element: <ProtectedRoute><UserProfile /></ProtectedRoute> 
      },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);