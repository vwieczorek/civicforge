import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import QuestList from './views/QuestList';
import QuestDetail from './views/QuestDetail';
import CreateQuest from './views/CreateQuest';
import UserProfile from './views/UserProfile';
import Login from './views/Login';
import Register from './views/Register';
import NotFound from './views/NotFound';
import ProtectedRoute from './components/auth/ProtectedRoute';
import ErrorBoundary from './components/common/ErrorBoundary';
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
      { path: 'login', element: <Login /> },
      { path: 'register', element: <Register /> },
      { path: 'users/:userId', element: <UserProfile /> },
      { path: '*', element: <NotFound /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>
  </React.StrictMode>
);