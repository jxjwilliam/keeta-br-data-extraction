import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [dir, target, repoRoot] = process.argv.slice(2);
if (!dir || !target || !repoRoot) throw new Error('参数：证据目录 XLSX目标 项目根目录');
const ev=JSON.parse(await fs.readFile(dir+'/evidence.json','utf8'));
const project=(await fs.readFile(repoRoot+'/README.md','utf8'))+'\n'+(await fs.readFile(repoRoot+'/project.md','utf8'));
const names=new Map([...project.matchAll(/^\|\s*\d+\s*\|\s*(\w+)\s*\|\s*([^|]+)\|/gm)].map(m=>[m[1],m[2].trim()]));
function excelLocalTime(iso) {
 const m=iso.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})/);
 if (!m) throw new Error('缺少 ISO 采集时间');
 return Date.UTC(...[+m[1],+m[2]-1,+m[3],+m[4],+m[5],+m[6]])/86400000+25569;
}
const keys=Object.keys(ev.record);const wb=Workbook.create();const data=wb.worksheets.add('30字段记录');const detail=wb.worksheets.add('字段核对');
data.getRange('A1:AD3').values=[keys.map(k=>names.get(k)||k),keys,keys.map(k=>k==='crawl_time' ? excelLocalTime(ev.record[k]) : ev.record[k])];
data.getRange('A1:AD3').format.font={name:'Arial',size:10};data.getRange('A1:AD2').format={fill:'#24445A',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true};
data.getRange('A1:AD3').format.columnWidth=19;data.getRange('A1:AD2').format.rowHeight=36;data.getRange('A3:AD3').format.rowHeight=90;data.getRange('A3:AD3').format.wrapText=true;
for(const col of ['E','K','N','T'])data.getRange(`${col}1:${col}3`).format.columnWidth=42;
data.getRange('E3').setNumberFormat('yyyy-mm-dd hh:mm:ss');
data.freezePanes.freezeRows(2);data.freezePanes.freezeColumns(1);data.showGridLines=false;
detail.showGridLines=false;detail.getRange('A2').values=[['Keeta 实时字段核对']];detail.getRange('A2').format.font={name:'Arial',size:14,bold:true};
detail.getRange('A4:E4').values=[['序号','字段代码','中文列名','采集值','来源或缺失原因']];
detail.getRange('A5:E34').values=keys.map((k,i)=>[i+1,k,names.get(k),ev.record[k],ev.field_sources[k]]);
detail.getRange('A4:E34').format.font={name:'Arial',size:10};detail.getRange('A4:E4').format={fill:'#24445A',font:{bold:true,color:'#FFFFFF'},rowHeight:28};detail.getRange('A5:E34').format.rowHeight=44;detail.getRange('A5:E34').format.wrapText=true;
for(const [col,width] of [['A',7],['B',35],['C',20],['D',60],['E',90]])detail.getRange(`${col}1:${col}40`).format.columnWidth=width;
detail.getRange('A36:B40').values=[['原始送达窗',ev.eta_raw],['时区',ev.timezone],['费用核算（分）',`${ev.record.product_final} + ${ev.record.delivery_final} + ${ev.record.service_final} = ${ev.record.total_final}`],['已应用优惠（分）',ev.qa.applied_discount_cents],['证据来源','同轮实时 Checkout XML 和截图，未提交订单']];detail.getRange('A36:B40').format.rowHeight=25;detail.getRange('A36:E40').format.wrapText=true; // 表格列宽保留
wb.recalculate();
console.log((await wb.inspect({kind:'table',range:"'30字段记录'!U1:AB3",include:'values,formulas',tableMaxRows:3,tableMaxCols:8,maxChars:2200})).ndjson);
await fs.writeFile(dir+'/preview-detail.png',new Uint8Array(await (await wb.render({sheetName:'字段核对',range:'A18:E34',scale:1})).arrayBuffer()));
await fs.writeFile(dir+'/preview-data.png',new Uint8Array(await (await wb.render({sheetName:'30字段记录',range:'U1:AD3',scale:1})).arrayBuffer()));
await (await SpreadsheetFile.exportXlsx(wb)).save(target);
console.log(target);
