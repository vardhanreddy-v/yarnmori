// Development preview adapter. Normal production startup uses uvicorn directly.
import {spawn} from 'node:child_process';
const args=process.argv.slice(2);
function option(name,fallback){const i=args.lastIndexOf(name);return i>=0?args[i+1]:fallback;}
const child=spawn('python',['-m','uvicorn','app:app','--host',option('--host','127.0.0.1'),'--port',option('--port','8000')],{stdio:'inherit'});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
child.on('exit',code=>process.exit(code??1));
