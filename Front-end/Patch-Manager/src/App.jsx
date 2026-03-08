// Commentez ou supprimez Authentication pour tester CreationPatch seule

// import Authentication from './Component/Authentification';
import './App.css'
import CreationPatch from './Component/Patch';

function App() {
  return (
    <div className="App">
      {/* <Authentication /> */}
      <CreationPatch/>
    </div>
  );
}

export default App;