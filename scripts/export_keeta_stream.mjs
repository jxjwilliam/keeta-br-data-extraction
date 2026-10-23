import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [source,target,repo]=process.argv.slice(2);
const rows=JSON.parse(await fs.readFile(source,'utf8'));
const keys=Object.keys(rows[0]);
const docs=(await fs.readFile(repo+'/README.md','utf8'))+'\n'+(await fs.readFile(repo+'/project.md','utf8'));
const names=new Map([...docs.matchAll(/^\|\s*\d+\s*\|\s*(\w+)\s*\|\s*([^|]+)\|/gm)].map(m=>[m[1],m[2].trim()]));
function localExcelTime(iso) { const m=iso?.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/); if (!m) return null; return Date.UTC(+m[1],+m[2]-1,+m[3],+m[4],+m[5],+m[6])/86400000+25569; }
const wb=Workbook.create(),sheet=wb.worksheets.add('连续采集');
sheet.getRangeByIndexes(0,0,rows.length+2,keys.length).values=[keys.map(k=>names.get(k)||k),keys,...rows.map(r=>keys.map(k=>k==='crawl_time'?localExcelTime(r[k]):r[k]))];
sheet.getRangeByIndexes(0,0,rows.length+2,keys.length).format={font:{name:'Arial',size:10},columnWidth:20,wrapText:true,rowHeight:32};
sheet.getRange('A1:AD2').format={fill:'#24445A',font:{bold:true,color:'#FFFFFF'},rowHeight:32};
for(const col of ['E','K','N','Q','T'])sheet.getRange(`${col}1:${col}${rows.length+2}`).format.columnWidth=42;
sheet.getRange(`E3:E${rows.length+2}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
sheet.freezePanes.freezeRows(2);sheet.showGridLines=false;wb.recalculate();
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
