#'==== 代码简介 ===================================================================
#'
#'@用途:地表(0cm)温度观测数据处理
#'@数据来源：国家气象科学数据中心中国地面气候资料日值数据集(V3.0)
#'@作者：曹斌（bin.cao@itpcas.ac.cn）
#'
#'=============================================================================

library(data.table)

remove(list = ls()) # clear

# ==== SETTING-UP =============================================================

# directory
dir_gst <- '~/OneDrive/GitHub/LST/data/OBS'
dir_out <- '~/OneDrive/GitHub/LST/data'

# outfile
outfile <- 'GSTObs.csv'

# make file
outfile <- file.path(dir_out, outfile)

flist <- list.files(dir_gst, pattern = '*.TXT')

# ==== IMPORT =================================================================

gst <- data.frame()

for (f in flist) {
  gsti <- fread(file.path(dir_gst, f))
  gst  <- rbind(gst, gsti)
}

colnames(gst) <- c('site','lat','lon','ele','year','month','day','gstAvg',
                   'gstMax','gstMin','gstAvgQC','gstMaxQC','gstMinQC')

gst$date <- as.Date(paste(gst$year, gst$month, gst$day, sep = '-'))
gst <- gst[, c('site','lat','lon','ele','date','gstAvg','gstMax','gstMin')]
gst$gstAvg <- gst$gstAvg/10
gst$gstMax <- gst$gstMax/10
gst$gstMin <- gst$gstMin/10

# ==== CHECK ==================================================================

gsti <- subset(gst, site == '50136')

plot(gsti$date, gsti$gstAvg, 'l', lwd = 1.5,
     xlab = '', 
     ylab = expression('Ground surface temperature ('*degree*C*')'),
     xlim = c(as.Date('2019-01-01'), as.Date('2019-12-31')))

# ==== EXPORT =================================================================

fwrite(gst, outfile)
